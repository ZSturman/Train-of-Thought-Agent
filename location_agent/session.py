from __future__ import annotations

import uuid
from typing import Callable

from location_agent.logging import EventLogger
from location_agent.memory import LabelConflictError, MemoryStore
from location_agent.models import (
    NormalizedObservation,
    ObservationError,
    SensorObservation,
    SensorObservationError,
    normalize_label_name,
)

InputFunc = Callable[[str], str]
OutputFunc = Callable[[str], None]

PHASE_NUMBER = 4
PHASE_TITLE = "First-Class Labels"

_WELCOME_BANNER = f"""\
========================================================
  Tree-of-Thought Location Agent
  Phase {PHASE_NUMBER}: {PHASE_TITLE}
========================================================

This agent learns location models from grayscale observations
and now stores labels as first-class nodes with aliases,
rename history, and reusable location identity.

HOW IT WORKS
  1. You enter a grayscale value (a decimal from 0.0 to 1.0).
  2. If the agent recognizes it, it guesses the canonical label
     and asks you to confirm.
  3. Reusing an existing location label reinforces that same learned
     location instead of forcing a different name.
  4. When one location has confirmed observations across a wider span,
     values inside that span default to the same location unless later
     evidence suggests a split.
  5. If the label needs refinement later, you can rename it while
     preserving the old name as an alias.
  6. You can add extra aliases for any learned location label.
  7. Use 'sense /path/to/media' to test a file-backed sensor input.
  8. Type 'inspect' to review learned labels, aliases, and model stats.

Type 'quit' at any time to exit.
Type 'inspect' to view learned location models.
Type 'rename' to rename an existing label.
Type 'alias' to add an alias to an existing label.
Type 'sense /path/to/file' to learn or recognize a simulated sensor input.
Type 'reset' to clear all learned memory.
--------------------------------------------------------"""

_WELCOME_QUIET = "agent online"


class SessionController:
    """Interactive Phase 4 control loop with injectable I/O for testing."""

    def __init__(
        self,
        *,
        store: MemoryStore,
        event_logger: EventLogger,
        input_func: InputFunc = input,
        output_func: OutputFunc = print,
        session_id: str | None = None,
        quiet: bool = False,
    ):
        self.store = store
        self.event_logger = event_logger
        self.input_func = input_func
        self.output_func = output_func
        self.session_id = session_id or uuid.uuid4().hex
        self.quiet = quiet
        self._observations_this_session = 0
        self._locations_learned = 0
        self._correct_guesses = 0
        self._wrong_guesses = 0
        self._observations_merged = 0

    # -- prompt / message strings (quiet vs verbose) -----------------

    @property
    def _observation_prompt(self) -> str:
        if self.quiet:
            return "observation[0.0-1.0|quit]: "
        return "\nEnter a grayscale observation (0.0 to 1.0), or 'quit' to exit: "

    @property
    def _feedback_prompt(self) -> str:
        if self.quiet:
            return "correct?[1/0]: "
        return "Is this correct? (yes/no): "

    @property
    def _label_prompt(self) -> str:
        if self.quiet:
            return "label: "
        return "What location does this represent? Enter a label: "

    @property
    def _rename_source_prompt(self) -> str:
        if self.quiet:
            return "rename from: "
        return "Which existing canonical label or alias should I rename? "

    @property
    def _rename_target_prompt(self) -> str:
        if self.quiet:
            return "rename to: "
        return "What should the new canonical label be? "

    @property
    def _alias_source_prompt(self) -> str:
        if self.quiet:
            return "alias for: "
        return "Which existing canonical label or alias should receive a new alias? "

    @property
    def _alias_target_prompt(self) -> str:
        if self.quiet:
            return "alias name: "
        return "What alias should I add? "

    @property
    def _sensor_path_prompt(self) -> str:
        if self.quiet:
            return "sensor path: "
        return "Enter the path to the image, video, or other media file: "

    def _msg_guess(self, label: str, confidence: float) -> str:
        if self.quiet:
            return f"guess: {label} (confidence={confidence:.2f})"
        pct = confidence * 100
        return f'I recognize this! My guess: "{label}" (confidence: {pct:.0f}%)'

    def _msg_ask_unknown(self) -> str:
        if self.quiet:
            return "where am i"
        return "This is a new observation — I haven't seen this value before."

    def _msg_uncertain_guess(self, label: str, confidence: float) -> str:
        if self.quiet:
            return f"uncertain: {label} (confidence={confidence:.2f})"
        pct = confidence * 100
        return (
            f'I\'m not very sure, but my best guess is: "{label}" '
            f"(confidence: {pct:.0f}%)"
        )

    def _msg_near_collision(self, existing_label: str, existing_proto: float) -> str:
        if self.quiet:
            return f"near: {existing_label} @ {existing_proto:.6f}. new label?[yes/no]"
        return (
            f'This is very close to "{existing_label}" at {existing_proto:.6f}. '
            "Learn as a new location anyway? (yes/no)"
        )

    def _msg_label_reuse_conflict(
        self,
        reused_label: str,
        nearby_label: str,
        nearby_proto: float,
    ) -> str:
        if self.quiet:
            return f"reuse: {reused_label}. near {nearby_label} @ {nearby_proto:.6f}. keep reuse?[yes/no]"
        return (
            f'You entered "{reused_label}", but this observation is also very close to '
            f'"{nearby_label}" at {nearby_proto:.6f}. Keep reinforcing "{reused_label}"? (yes/no)'
        )

    def _msg_outlier_warning(self, label: str, prototype: float) -> str:
        if self.quiet:
            return f"outlier: far from {label} @ {prototype:.6f}. merge?[yes/no]"
        return (
            f'This observation is unusually far from "{label}" '
            f"(prototype {prototype:.6f}). Merge anyway? (yes/no)"
        )

    def _msg_ask_wrong(self) -> str:
        if self.quiet:
            return "where am i"
        return "Got it — my guess was wrong. What is the correct location label?"

    def _msg_learned(self, obs_val: float, label: str) -> str:
        if self.quiet:
            return ""
        return f'Learned! {obs_val:.6f} → "{label}"'

    def _msg_reused(self, obs_val: float, label: str) -> str:
        if self.quiet:
            return ""
        return f'Reinforced existing location "{label}" with {obs_val:.6f}.'

    def _msg_correct_confirmed(self) -> str:
        if self.quiet:
            return ""
        return "Great — my memory is reinforced."

    def _msg_corrected(self, old_label: str, new_label: str) -> str:
        if self.quiet:
            return ""
        return (
            f'Updated! Corrected "{old_label}" → "{new_label}". '
            "The old name still resolves as an alias."
        )

    def _msg_invalid_feedback(self) -> str:
        if self.quiet:
            return "invalid feedback: enter 1 or 0"
        return "Please answer yes or no (y/n also accepted)."

    def _msg_reset_confirm(self) -> str:
        if self.quiet:
            return "reset all memory?[yes/no]: "
        return "Are you sure? This will delete all learned locations. (yes/no): "

    def _msg_reset_done(self, count: int) -> str:
        if self.quiet:
            return f"reset: {count} models cleared"
        return f"Memory reset — {count} location model(s) removed."

    def _msg_reset_cancelled(self) -> str:
        if self.quiet:
            return "reset cancelled"
        return "Reset cancelled — memory unchanged."

    def _msg_label_not_found(self, name: str) -> str:
        if self.quiet:
            return f"label not found: {name}"
        return f'I could not find a label or alias named "{name}".'

    def _msg_label_conflict(self, message: str) -> str:
        if self.quiet:
            return f"label conflict: {message}"
        return f"{message}. Please choose a different name."

    def _msg_renamed(self, old_name: str, new_name: str) -> str:
        if self.quiet:
            return f"renamed: {old_name} -> {new_name}"
        return f'Renamed "{old_name}" → "{new_name}". The old name remains as an alias.'

    def _msg_alias_added(self, alias: str, canonical_name: str) -> str:
        if self.quiet:
            return f"alias-added: {alias} -> {canonical_name}"
        return f'Added alias "{alias}" for "{canonical_name}".'

    def _msg_no_change(self, label: str) -> str:
        if self.quiet:
            return f"unchanged: {label}"
        return f'No change — "{label}" already resolves to the same label node.'

    def _msg_sensor_known(self, media_kind: str) -> str:
        if self.quiet:
            return f"sensor: recognized {media_kind}"
        return f"I've seen this {media_kind} input before."

    def _msg_sensor_unknown(self, media_kind: str) -> str:
        if self.quiet:
            return f"sensor: new {media_kind}"
        return f"This {media_kind} input is new — I don't know its location yet."

    def _msg_sensor_learned(self, label: str, media_kind: str, created: bool) -> str:
        if self.quiet:
            return ""
        if created:
            return f'Learned a new location "{label}" from this {media_kind} input.'
        return f'Linked this {media_kind} input to the existing location "{label}".'

    def _format_inspect(self) -> str:
        models = self.store.inspect_models()
        if not models:
            return "No location models learned yet." if not self.quiet else "empty"

        lines = []
        if not self.quiet:
            lines.append("--- Learned Location Models ---")
            for model in models:
                aliases = ", ".join(model["aliases"]) if model["aliases"] else "-"
                rename_count = len(model["rename_history"])
                prototype = "n/a" if model["prototype"] is None else f"{model['prototype']:.6f}"
                lines.append(
                    f"  {model['canonical_name']:20s}  [{model['label_id']}]  "
                    f"aliases={aliases}  proto={prototype}  "
                    f"spread={model['spread']:.6f}  obs={model['observation_count']}  "
                    f"renames={rename_count}"
                )
            lines.append("-------------------------------")
        else:
            for model in models:
                aliases = ",".join(model["aliases"])
                prototype = "na" if model["prototype"] is None else f"{model['prototype']:.6f}"
                lines.append(
                    f"{model['canonical_name']}|{aliases}|{model['label_id']}|"
                    f"{prototype}|{model['spread']:.6f}|"
                    f"{model['observation_count']}|{len(model['rename_history'])}"
                )
        return "\n".join(lines)

    def _handle_reset(self) -> None:
        try:
            raw = self.input_func(self._msg_reset_confirm())
        except EOFError:
            return
        if raw.strip().lower() in {"1", "yes", "y"}:
            count = self.store.reset_memory()
            self.output_func(self._msg_reset_done(count))
            self.event_logger.log(
                "memory_mutation",
                session_id=self.session_id,
                mutation_kind="memory_reset",
                notes=f"user_reset_{count}_models",
            )
        else:
            self.output_func(self._msg_reset_cancelled())

    def _handle_rename(self) -> None:
        while True:
            source = self._prompt_text(self._rename_source_prompt)
            if self.store.lookup_by_label_name(source) is None:
                self.output_func(self._msg_label_not_found(source))
                continue
            break

        while True:
            target = self._prompt_text(self._rename_target_prompt)
            try:
                old_snapshot, new_snapshot = self.store.rename_label(source, target)
            except LabelConflictError as exc:
                self.output_func(self._msg_label_conflict(str(exc)))
                continue
            break

        if old_snapshot == new_snapshot:
            self.output_func(self._msg_no_change(new_snapshot["canonical_name"]))
            return

        self.output_func(
            self._msg_renamed(
                old_snapshot["canonical_name"],
                new_snapshot["canonical_name"],
            )
        )
        self.event_logger.log(
            "memory_mutation",
            session_id=self.session_id,
            mutation_kind="label_renamed",
            old_record=old_snapshot,
            new_record=new_snapshot,
            notes="rename_command",
        )

    def _handle_alias(self) -> None:
        while True:
            source = self._prompt_text(self._alias_source_prompt)
            resolved = self.store.lookup_by_label_name(source)
            if resolved is None:
                self.output_func(self._msg_label_not_found(source))
                continue
            break

        while True:
            alias = self._prompt_text(self._alias_target_prompt)
            try:
                old_snapshot, new_snapshot = self.store.add_alias(source, alias)
            except LabelConflictError as exc:
                self.output_func(self._msg_label_conflict(str(exc)))
                continue
            break

        if old_snapshot == new_snapshot:
            self.output_func(self._msg_no_change(alias))
            return

        self.output_func(self._msg_alias_added(alias.strip(), new_snapshot["canonical_name"]))
        self.event_logger.log(
            "memory_mutation",
            session_id=self.session_id,
            mutation_kind="label_alias_added",
            old_record=old_snapshot,
            new_record=new_snapshot,
            notes="alias_command",
        )

    def _prompt_sensor_path(self) -> str:
        while True:
            try:
                raw = self.input_func(self._sensor_path_prompt)
            except EOFError as exc:
                raise EOFError("sensor path input closed") from exc
            stripped = raw.strip()
            if stripped:
                return stripped
            self.output_func("sensor path cannot be empty")

    def _handle_sensor_input(self, inline_path: str | None = None) -> None:
        raw_path = inline_path.strip() if inline_path else ""
        while True:
            candidate = raw_path or self._prompt_sensor_path()
            try:
                sensor_observation = SensorObservation.from_path(candidate)
            except SensorObservationError as exc:
                self.output_func(str(exc))
                raw_path = ""
                continue
            break

        self._observations_this_session += 1
        self.event_logger.log(
            "observation",
            session_id=self.session_id,
            sensor_observation=sensor_observation,
            notes="sensor_input",
        )
        recognized = self.store.lookup_sensor_binding(sensor_observation.fingerprint)

        if recognized is not None:
            _, model, label = recognized
            guessed_label = label.canonical_name
            self.output_func(self._msg_sensor_known(sensor_observation.media_kind))
            self.output_func(self._msg_guess(guessed_label, 1.0))
            self.event_logger.log(
                "decision",
                session_id=self.session_id,
                sensor_observation=sensor_observation,
                guessed_label=guessed_label,
                confidence=1.0,
                notes="guess_known_location_from_sensor",
            )
            feedback = self._prompt_feedback()
            self.event_logger.log(
                "feedback",
                session_id=self.session_id,
                sensor_observation=sensor_observation,
                guessed_label=guessed_label,
                confidence=1.0,
                feedback=feedback,
            )
            if feedback == 1:
                old_snapshot, new_snapshot, _ = self.store.bind_sensor_observation(
                    sensor_observation,
                    guessed_label,
                )
                self._correct_guesses += 1
                self.output_func(self._msg_correct_confirmed())
                self.event_logger.log(
                    "memory_mutation",
                    session_id=self.session_id,
                    sensor_observation=sensor_observation,
                    guessed_label=guessed_label,
                    confidence=1.0,
                    feedback=feedback,
                    mutation_kind="sensor_binding_reinforced",
                    old_record=old_snapshot,
                    new_record=new_snapshot,
                    notes="sensor_guess_confirmed",
                )
                return

            self.output_func(self._msg_ask_wrong())
            corrected_label = self._prompt_label()
            old_snapshot, new_snapshot, created = self.store.bind_sensor_observation(
                sensor_observation,
                corrected_label,
            )
            self._wrong_guesses += 1
            self.output_func(
                self._msg_sensor_learned(
                    new_snapshot["canonical_name"],
                    sensor_observation.media_kind,
                    created,
                )
            )
            self.event_logger.log(
                "memory_mutation",
                session_id=self.session_id,
                sensor_observation=sensor_observation,
                guessed_label=guessed_label,
                confidence=1.0,
                feedback=feedback,
                mutation_kind="sensor_binding_updated",
                old_record=old_snapshot,
                new_record=new_snapshot,
                notes="sensor_guess_corrected",
            )
            return

        self.event_logger.log(
            "decision",
            session_id=self.session_id,
            sensor_observation=sensor_observation,
            notes="ask_for_sensor_location_label",
        )
        self.output_func(self._msg_sensor_unknown(sensor_observation.media_kind))
        label = self._prompt_label()
        self.event_logger.log(
            "feedback",
            session_id=self.session_id,
            sensor_observation=sensor_observation,
            guessed_label=label,
            notes="user_supplied_label_for_sensor",
        )
        old_snapshot, new_snapshot, created = self.store.bind_sensor_observation(
            sensor_observation,
            label,
        )
        self.output_func(
            self._msg_sensor_learned(
                new_snapshot["canonical_name"],
                sensor_observation.media_kind,
                created,
            )
        )
        self.event_logger.log(
            "memory_mutation",
            session_id=self.session_id,
            sensor_observation=sensor_observation,
            guessed_label=label,
            mutation_kind="sensor_binding_created",
            old_record=old_snapshot,
            new_record=new_snapshot,
            notes="sensor_learned",
        )

    # -- main loop ---------------------------------------------------

    def run(self) -> None:
        if self.quiet:
            self.output_func(_WELCOME_QUIET)
        else:
            self.output_func(_WELCOME_BANNER)
        self.event_logger.log("session_start", session_id=self.session_id, notes="agent_online")
        while True:
            try:
                raw = self.input_func(self._observation_prompt)
            except EOFError:
                self._close_session("eof")
                return
            stripped = raw.strip()
            lowered = stripped.lower()
            command, _, remainder = stripped.partition(" ")
            if lowered == "quit":
                self._close_session("user_quit")
                return
            if lowered == "inspect":
                self.output_func(self._format_inspect())
                continue
            if lowered == "reset":
                self._handle_reset()
                continue
            if lowered == "rename":
                try:
                    self._handle_rename()
                except EOFError:
                    self._close_session("eof")
                    return
                continue
            if lowered == "alias":
                try:
                    self._handle_alias()
                except EOFError:
                    self._close_session("eof")
                    return
                continue
            if command.lower() == "sense":
                try:
                    self._handle_sensor_input(remainder)
                except EOFError:
                    self._close_session("eof")
                    return
                continue
            try:
                observation = NormalizedObservation.parse(raw)
            except ObservationError as exc:
                self.output_func(str(exc))
                continue
            self._observations_this_session += 1
            try:
                self._handle_observation(observation)
            except EOFError:
                self._close_session("eof")
                return

    def _handle_observation(self, observation: NormalizedObservation) -> None:
        self.event_logger.log("observation", session_id=self.session_id, observation=observation)
        model, confidence = self.store.find_nearest(observation)

        if model is not None and confidence >= self.store.guess_threshold:
            guess_snapshot = self.store.snapshot_location(model)
            guessed_label = guess_snapshot["canonical_name"]
            self.output_func(self._msg_guess(guessed_label, confidence))
            self.event_logger.log(
                "decision",
                session_id=self.session_id,
                observation=observation,
                guessed_label=guessed_label,
                confidence=confidence,
                notes="guess_known_location",
            )
            feedback = self._prompt_feedback()
            self.event_logger.log(
                "feedback",
                session_id=self.session_id,
                observation=observation,
                guessed_label=guessed_label,
                confidence=confidence,
                feedback=feedback,
            )
            if feedback == 1:
                if self.store.is_outlier(model, observation.value):
                    self.output_func(self._msg_outlier_warning(guessed_label, model.prototype))
                    merge_ok = self._prompt_feedback()
                    if merge_ok != 1:
                        self._correct_guesses += 1
                        msg = self._msg_correct_confirmed()
                        if msg:
                            self.output_func(msg)
                        return

                old_model, new_model = self.store.record_correct_guess(
                    observation,
                    matched_model=model,
                )
                self._correct_guesses += 1
                self._observations_merged += 1
                msg = self._msg_correct_confirmed()
                if msg:
                    self.output_func(msg)
                self.event_logger.log(
                    "memory_mutation",
                    session_id=self.session_id,
                    observation=observation,
                    guessed_label=guessed_label,
                    confidence=confidence,
                    feedback=feedback,
                    mutation_kind="merge_observation",
                    old_record=self.store.snapshot_location(old_model),
                    new_record=self.store.snapshot_location(new_model),
                    notes="correct_guess_merged",
                )
                return

            self.output_func(self._msg_ask_wrong())
            while True:
                corrected_label = self._prompt_label()
                try:
                    old_snapshot, new_snapshot = self.store.correct_location(
                        observation,
                        corrected_label,
                        matched_model=model,
                    )
                except LabelConflictError as exc:
                    self.output_func(self._msg_label_conflict(str(exc)))
                    continue
                break

            self._wrong_guesses += 1
            msg = self._msg_corrected(
                old_snapshot["canonical_name"],
                new_snapshot["canonical_name"],
            )
            if msg:
                self.output_func(msg)
            self.event_logger.log(
                "memory_mutation",
                session_id=self.session_id,
                observation=observation,
                guessed_label=guessed_label,
                confidence=confidence,
                feedback=feedback,
                mutation_kind="label_correction",
                old_record=old_snapshot,
                new_record=new_snapshot,
                notes="wrong_guess_relabel",
            )
            return

        if model is not None and confidence > 0.0:
            guess_snapshot = self.store.snapshot_location(model)
            guessed_label = guess_snapshot["canonical_name"]
            self.output_func(self._msg_uncertain_guess(guessed_label, confidence))
            self.event_logger.log(
                "decision",
                session_id=self.session_id,
                observation=observation,
                guessed_label=guessed_label,
                confidence=confidence,
                notes="uncertain_guess",
            )
            feedback = self._prompt_feedback()
            self.event_logger.log(
                "feedback",
                session_id=self.session_id,
                observation=observation,
                guessed_label=guessed_label,
                confidence=confidence,
                feedback=feedback,
            )
            if feedback == 1:
                old_model, new_model = self.store.record_correct_guess(
                    observation,
                    matched_model=model,
                )
                self._correct_guesses += 1
                self._observations_merged += 1
                msg = self._msg_correct_confirmed()
                if msg:
                    self.output_func(msg)
                self.event_logger.log(
                    "memory_mutation",
                    session_id=self.session_id,
                    observation=observation,
                    guessed_label=guessed_label,
                    confidence=confidence,
                    feedback=feedback,
                    mutation_kind="merge_observation",
                    old_record=self.store.snapshot_location(old_model),
                    new_record=self.store.snapshot_location(new_model),
                    notes="uncertain_guess_confirmed_merged",
                )
                return

            self.output_func(self._msg_ask_unknown())
            label = self._prompt_label()
            self.event_logger.log(
                "feedback",
                session_id=self.session_id,
                observation=observation,
                guessed_label=label,
                confidence=confidence,
                notes="user_supplied_label_after_uncertain_rejection",
            )
            self._wrong_guesses += 1
            self._learn_with_collision_check(observation, label, confidence)
            return

        self.event_logger.log(
            "decision",
            session_id=self.session_id,
            observation=observation,
            confidence=confidence,
            notes="ask_for_location_label",
        )
        self.output_func(self._msg_ask_unknown())
        label = self._prompt_label()
        self.event_logger.log(
            "feedback",
            session_id=self.session_id,
            observation=observation,
            guessed_label=label,
            confidence=confidence,
            notes="user_supplied_label",
        )
        self._learn_with_collision_check(observation, label, confidence)

    def _learn_with_collision_check(
        self,
        observation: NormalizedObservation,
        label: str,
        confidence: float,
    ) -> None:
        while True:
            normalized_label = normalize_label_name(label)
            resolved = self.store.lookup_by_label_name(normalized_label)
            if resolved is not None:
                existing_model, _ = resolved
                collision = self.store.find_near_collision(
                    observation,
                    exclude_location_id=existing_model.location_id,
                )
                if collision is not None and collision.prototype is not None:
                    collision_snapshot = self.store.snapshot_location(collision)
                    self.output_func(
                        self._msg_label_reuse_conflict(
                            normalized_label,
                            collision_snapshot["canonical_name"],
                            collision.prototype,
                        )
                    )
                    if self._prompt_feedback() != 1:
                        label = self._prompt_label()
                        continue

                if self.store.is_outlier(existing_model, observation.value):
                    prototype = existing_model.prototype if existing_model.prototype is not None else 0.0
                    self.output_func(self._msg_outlier_warning(normalized_label, prototype))
                    if self._prompt_feedback() != 1:
                        label = self._prompt_label()
                        continue

                old_model, new_model = self.store.reinforce_named_location(
                    observation,
                    normalized_label,
                )
                self._observations_merged += 1
                msg = self._msg_reused(observation.value, normalized_label)
                if msg:
                    self.output_func(msg)
                self.event_logger.log(
                    "memory_mutation",
                    session_id=self.session_id,
                    observation=observation,
                    guessed_label=normalized_label,
                    confidence=confidence,
                    mutation_kind="merge_observation",
                    old_record=self.store.snapshot_location(old_model),
                    new_record=self.store.snapshot_location(new_model),
                    notes="existing_label_reused",
                )
                return

            collision = self.store.find_near_collision(observation)
            if collision is not None:
                collision_snapshot = self.store.snapshot_location(collision)
                self.output_func(
                    self._msg_near_collision(
                        collision_snapshot["canonical_name"],
                        collision.prototype,
                    )
                )
                proceed = self._prompt_feedback()
                if proceed != 1:
                    self.output_func("Skipped — observation not learned." if not self.quiet else "skipped")
                    return

            try:
                old_model, new_model = self.store.learn_location(observation, normalized_label)
            except LabelConflictError as exc:
                self.output_func(self._msg_label_conflict(str(exc)))
                label = self._prompt_label()
                continue
            break

        self._locations_learned += 1
        msg = self._msg_learned(observation.value, normalized_label)
        if msg:
            self.output_func(msg)
        self.event_logger.log(
            "memory_mutation",
            session_id=self.session_id,
            observation=observation,
            confidence=confidence,
            mutation_kind="model_created",
            old_record=old_model,
            new_record=self.store.snapshot_location(new_model),
            notes="new_location_learned",
        )

    def _prompt_feedback(self) -> int:
        while True:
            try:
                raw = self.input_func(self._feedback_prompt)
            except EOFError as exc:
                raise EOFError("feedback input closed") from exc
            stripped = raw.strip().lower()
            if stripped in {"1", "yes", "y"}:
                return 1
            if stripped in {"0", "no", "n"}:
                return 0
            self.output_func(self._msg_invalid_feedback())

    def _prompt_text(self, prompt: str) -> str:
        while True:
            try:
                raw = self.input_func(prompt)
            except EOFError as exc:
                raise EOFError("text input closed") from exc
            stripped = raw.strip()
            if stripped:
                return stripped
            self.output_func("label cannot be empty")

    def _prompt_label(self) -> str:
        return self._prompt_text(self._label_prompt)

    def _close_session(self, note: str) -> None:
        self.event_logger.log("session_end", session_id=self.session_id, notes=note)
        if not self.quiet:
            self.output_func("")
            self.output_func("--- Session Summary ---")
            self.output_func(f"  Observations entered : {self._observations_this_session}")
            self.output_func(f"  New locations learned : {self._locations_learned}")
            self.output_func(f"  Observations merged  : {self._observations_merged}")
            self.output_func(f"  Correct guesses      : {self._correct_guesses}")
            self.output_func(f"  Wrong guesses        : {self._wrong_guesses}")
            self.output_func("-----------------------")
        self.output_func("goodbye")

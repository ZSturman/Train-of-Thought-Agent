from __future__ import annotations

import uuid
from typing import Callable

from location_agent.logging import EventLogger
from location_agent.memory import MemoryStore
from location_agent.models import NormalizedObservation, ObservationError

InputFunc = Callable[[str], str]
OutputFunc = Callable[[str], None]

PHASE_NUMBER = 3
PHASE_TITLE = "Multi-Observation Location Models"

_WELCOME_BANNER = f"""\
========================================================
  Tree-of-Thought Location Agent
  Phase {PHASE_NUMBER}: {PHASE_TITLE}
========================================================

This agent learns to associate grayscale observations
with location labels. It remembers what you teach it
and tries to guess on future observations.

HOW IT WORKS
  1. You enter a grayscale value (a decimal from 0.0 to 1.0).
  2. If the agent recognizes it (exact or close match),
     it guesses the location and asks you to confirm.
  3. If the agent is unsure, it shows its best guess
     but asks you to confirm or provide a label.
  4. If the agent does NOT recognize it, it asks you
     to provide a location label so it can learn.
  5. Confirmed observations are merged into the location
     model, refining its prototype over time.

Type 'quit' at any time to exit.
Type 'inspect' to view learned location models.
Type 'reset' to clear all learned memory.
--------------------------------------------------------"""

_WELCOME_QUIET = "agent online"


class SessionController:
    """Interactive Phase 3 control loop with injectable I/O for testing."""

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

    def _msg_guess(self, label: str, confidence: float) -> str:
        if self.quiet:
            return f"guess: {label} (confidence={confidence:.2f})"
        pct = confidence * 100
        return f"I recognize this! My guess: \"{label}\" (confidence: {pct:.0f}%)"

    def _msg_ask_unknown(self) -> str:
        if self.quiet:
            return "where am i"
        return "This is a new observation — I haven't seen this value before."

    def _msg_uncertain_guess(self, label: str, confidence: float) -> str:
        if self.quiet:
            return f"uncertain: {label} (confidence={confidence:.2f})"
        pct = confidence * 100
        return (
            f"I'm not very sure, but my best guess is: \"{label}\" "
            f"(confidence: {pct:.0f}%)"
        )

    def _msg_near_collision(self, existing_label: str, existing_proto: float) -> str:
        if self.quiet:
            return f"near: {existing_label} @ {existing_proto:.6f}. new label?[yes/no]"
        return (
            f"This is very close to \"{existing_label}\" at {existing_proto:.6f}. "
            f"Learn as a new location anyway? (yes/no)"
        )

    def _msg_outlier_warning(self, label: str, prototype: float) -> str:
        if self.quiet:
            return f"outlier: far from {label} @ {prototype:.6f}. merge?[yes/no]"
        return (
            f"This observation is unusually far from \"{label}\" "
            f"(prototype {prototype:.6f}). Merge anyway? (yes/no)"
        )

    def _msg_ask_wrong(self) -> str:
        if self.quiet:
            return "where am i"
        return "Got it — my guess was wrong. What is the correct location?"

    def _msg_learned(self, obs_val: float, label: str) -> str:
        if self.quiet:
            return ""
        return f"Learned! {obs_val:.6f} → \"{label}\""

    def _msg_correct_confirmed(self) -> str:
        if self.quiet:
            return ""
        return "Great — my memory is reinforced."

    def _msg_corrected(self, old_label: str, new_label: str) -> str:
        if self.quiet:
            return ""
        return f"Updated! Corrected \"{old_label}\" → \"{new_label}\" for this observation."

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

    def _format_inspect(self) -> str:
        models = self.store.inspect_models()
        if not models:
            return "No location models learned yet." if not self.quiet else "empty"
        lines = []
        if not self.quiet:
            lines.append("--- Learned Location Models ---")
            for m in models:
                lines.append(
                    f"  {m['label']:20s}  proto={m['prototype']:.6f}  "
                    f"spread={m['spread']:.6f}  obs={m['observation_count']}  "
                    f"correct={m['correct_count']}  wrong={m['incorrect_count']}"
                )
            lines.append("-------------------------------")
        else:
            for m in models:
                lines.append(
                    f"{m['label']}|{m['prototype']:.6f}|{m['spread']:.6f}|{m['observation_count']}"
                )
        return "\n".join(lines)

    def _handle_reset(self) -> None:
        """Prompt for confirmation and reset all learned memory."""
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
            stripped = raw.strip().lower()
            if stripped == "quit":
                self._close_session("user_quit")
                return
            if stripped == "inspect":
                self.output_func(self._format_inspect())
                continue
            if stripped == "reset":
                self._handle_reset()
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
            # Confident guess (exact or close match).
            self.output_func(self._msg_guess(model.label, confidence))
            self.event_logger.log(
                "decision",
                session_id=self.session_id,
                observation=observation,
                guessed_label=model.label,
                confidence=confidence,
                notes="guess_known_location",
            )
            feedback = self._prompt_feedback()
            self.event_logger.log(
                "feedback",
                session_id=self.session_id,
                observation=observation,
                guessed_label=model.label,
                confidence=confidence,
                feedback=feedback,
            )
            if feedback == 1:
                # Check for outlier before merging.
                if self.store.is_outlier(model, observation.value):
                    self.output_func(self._msg_outlier_warning(model.label, model.prototype))
                    merge_ok = self._prompt_feedback()
                    if merge_ok != 1:
                        # User declined outlier merge — still count as correct guess
                        # but do not merge the observation value.
                        self._correct_guesses += 1
                        msg = self._msg_correct_confirmed()
                        if msg:
                            self.output_func(msg)
                        return

                old_model, new_model = self.store.record_correct_guess(
                    observation, matched_model=model,
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
                    guessed_label=model.label,
                    confidence=confidence,
                    feedback=feedback,
                    mutation_kind="merge_observation",
                    old_record=old_model,
                    new_record=new_model,
                    notes="correct_guess_merged",
                )
                return
            old_label = model.label
            self.output_func(self._msg_ask_wrong())
            corrected_label = self._prompt_label()
            old_model, new_model = self.store.correct_location(
                observation, corrected_label, matched_model=model,
            )
            self._wrong_guesses += 1
            msg = self._msg_corrected(old_label, corrected_label)
            if msg:
                self.output_func(msg)
            self.event_logger.log(
                "memory_mutation",
                session_id=self.session_id,
                observation=observation,
                guessed_label=model.label,
                confidence=confidence,
                feedback=feedback,
                mutation_kind="label_correction",
                old_record=old_model,
                new_record=new_model,
                notes="wrong_guess_relabel",
            )
            return

        if model is not None and confidence > 0.0:
            # Uncertain match — show best guess but ask for confirmation.
            self.output_func(self._msg_uncertain_guess(model.label, confidence))
            self.event_logger.log(
                "decision",
                session_id=self.session_id,
                observation=observation,
                guessed_label=model.label,
                confidence=confidence,
                notes="uncertain_guess",
            )
            feedback = self._prompt_feedback()
            self.event_logger.log(
                "feedback",
                session_id=self.session_id,
                observation=observation,
                guessed_label=model.label,
                confidence=confidence,
                feedback=feedback,
            )
            if feedback == 1:
                old_model, new_model = self.store.record_correct_guess(
                    observation, matched_model=model,
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
                    guessed_label=model.label,
                    confidence=confidence,
                    feedback=feedback,
                    mutation_kind="merge_observation",
                    old_record=old_model,
                    new_record=new_model,
                    notes="uncertain_guess_confirmed_merged",
                )
                return
            # User rejected the uncertain guess — treat as unknown, ask for label.
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

        # No match at all — ask for label.
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
        """Learn a new location, warning if a near-collision exists."""
        collision = self.store.find_near_collision(observation)
        if collision is not None:
            self.output_func(self._msg_near_collision(collision.label, collision.prototype))
            proceed = self._prompt_feedback()
            if proceed != 1:
                self.output_func(
                    "Skipped — observation not learned."
                    if not self.quiet
                    else "skipped"
                )
                return

        old_model, new_model = self.store.learn_location(observation, label)
        self._locations_learned += 1
        msg = self._msg_learned(observation.value, label)
        if msg:
            self.output_func(msg)
        self.event_logger.log(
            "memory_mutation",
            session_id=self.session_id,
            observation=observation,
            confidence=confidence,
            mutation_kind="model_created",
            old_record=old_model,
            new_record=new_model,
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

    def _prompt_label(self) -> str:
        while True:
            try:
                raw = self.input_func(self._label_prompt)
            except EOFError as exc:
                raise EOFError("label input closed") from exc
            label = raw.strip()
            if label:
                return label
            self.output_func("label cannot be empty")

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

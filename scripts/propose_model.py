#!/usr/bin/env python3
"""Submit one pending ASX IOMR proposal through the SCL model service.

The script does not approve or commit. A trusted reviewer signature is
required before canonical nodes are written. Re-running it will not stack
a second open proposal.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

INFERENCE = (
    "Inferred while consolidating the ASX IOMR v0.2 candidate from SCL issue 22, "
    "including RN-05.13, into an ASX-owned model. This is an AI inference, not a human approval."
)
GAPS = (
    "Reference behaviour is locally tested in one process. Distributed linearizability, "
    "production signatures, and an implementation developed outside this repository are not shown."
)

SOURCES = {
    "protocol": "docs/protocol.md",
    "arbitration": "docs/arbitration.md",
    "security": "docs/security.md",
    "conformance": "docs/conformance.md",
}

INTENTS = [
    (
        "intent-semantic-integrity",
        "Semantic integrity",
        "Independent agents must agree the declared semantic references and the authoritative "
        "starting state before a consequential transition, or they must stop.",
        ("protocol", "anchor-intent-semantic-integrity"),
    ),
    (
        "intent-deterministic-arbitration",
        "Deterministic arbitration",
        "Conflicting proposals must produce one governed decision that another implementation "
        "can recompute without using message arrival order.",
        ("arbitration", "anchor-intent-deterministic-arbitration"),
    ),
    (
        "intent-replay-safety",
        "Replay safety",
        "Invalid, duplicated, stale, or unauthorised exchanges must not create an unintended "
        "state change or a second effect.",
        ("protocol", "anchor-intent-replay-safety"),
    ),
]

OUTCOMES = [
    ("outcome-matching-references", "Matching semantic references", "intent-semantic-integrity",
     ["model-semantic-agreement"], "protocol", "anchor-outcome-matching-references",
     "Byte equality of the canonical semantic-reference token.",
     "Agents name the same published semantic reference before a transition."),
    ("outcome-pre-state", "Verified pre-transition state", "intent-semantic-integrity",
     ["model-semantic-agreement"], "protocol", "anchor-outcome-pre-state",
     "A commit succeeds only when the stored parent hash equals the certified parent hash.",
     "The parent state is checked at the same boundary as the state change."),
    ("outcome-joint-certification", "Joint decision certification", "intent-semantic-integrity",
     ["model-semantic-agreement"], "protocol", "anchor-outcome-joint-certification",
     "Independent checks cover one canonical decision encoding.",
     "A certified decision is the canonical decision bytes, not a local paraphrase."),
    ("outcome-identical-validation-results", "Identical validation results", "intent-semantic-integrity",
     ["model-semantic-agreement"], "protocol", "anchor-outcome-identical-validation-results",
     "The same round record yields the same transcript, digest, challenge, ranking, winner, and rejections.",
     "Independent implementations report the same validation result for one record."),
    ("outcome-fail-closed", "Fail closed without agreement", "intent-semantic-integrity",
     ["model-semantic-agreement"], "protocol", "anchor-outcome-fail-closed",
     "Disagreement leaves the parent hash and the effect log unchanged.",
     "Missing agreement produces no state change and no effect."),
    ("outcome-ranking", "Deterministic ranking", "intent-deterministic-arbitration",
     ["model-governed-arbitration"], "arbitration", "anchor-outcome-ranking",
     "One winner from descending policy priority, then the lowest unsigned tie digest.",
     "Eligibility, priority, and the challenge-bound tie-break are functions of the authenticated record."),
    ("outcome-fairness", "Declared fairness", "intent-deterministic-arbitration",
     ["model-governed-arbitration", "model-policy-pinning"], "arbitration", "anchor-outcome-fairness",
     "A max-wins cap changes ranking only when the pinned policy declares it.",
     "Fairness is the published directive, not a hidden scheduler."),
    ("outcome-recorded-rejection", "Recorded rejection of losers", "intent-deterministic-arbitration",
     ["model-governed-arbitration"], "arbitration", "anchor-outcome-recorded-rejection",
     "Every eligible identity other than the winner has an explicit rejection code.",
     "Losing proposals are recorded and are not silently dropped or rebased."),
    ("outcome-recomputation", "Third-party recomputation", "intent-deterministic-arbitration",
     ["model-governed-arbitration"], "arbitration", "anchor-outcome-recomputation",
     "A third party recomputes the same winner from the authenticated record.",
     "The decision can be checked without trusting the selector's private choice."),
    ("outcome-one-successor", "One successor per parent", "intent-deterministic-arbitration",
     ["model-governed-arbitration"], "arbitration", "anchor-outcome-one-successor",
     "At most one committed successor is accepted for a parent hash.",
     "Selection is not commitment. The successor commits only against the expected parent."),
    ("outcome-replay-detection", "Durable replay detection", "intent-replay-safety",
     ["model-replay-protected-exchange"], "protocol", "anchor-outcome-replay-detection",
     "A repeated replay key returns the original receipt.",
     "A stored key is recognised after the process that wrote it has stopped."),
    ("outcome-atomic-rejection", "Atomic rejection", "intent-replay-safety",
     ["model-replay-protected-exchange"], "protocol", "anchor-outcome-atomic-rejection",
     "A halt returns one rejection code and does not change state.",
     "Rejection is observable and does not leave a partial effect."),
    ("outcome-no-duplicate", "No duplicate committed effect", "intent-replay-safety",
     ["model-replay-protected-exchange"], "protocol", "anchor-outcome-no-duplicate",
     "A committed replay key does not run its effect a second time.",
     "Retries of a committed transition do not create a second effect."),
    ("outcome-recovery", "Recovery after interruption", "intent-replay-safety",
     ["model-replay-protected-exchange"], "protocol", "anchor-outcome-recovery",
     "A restarted journal resumes the stored successor without inventing another.",
     "Interruption does not authorise a second successor."),
    ("outcome-consistent-failure", "Consistent failure behaviour", "intent-replay-safety",
     ["model-replay-protected-exchange"], "protocol", "anchor-outcome-consistent-failure",
     "The same malformed input yields the same rejection code.",
     "Implementations share one precedence list for rejection codes."),
]

REQUIREMENTS = [
    ("requirement-matching-semantic-references", "Matching semantic references", "model-semantic-agreement",
     "The implementation SHALL treat two semantic references as the same publication only when their canonical tokens are byte-equal.",
     "Given two tokens, reference equality is true only when the bytes are equal, and a mismatch produces no commit.",
     [("protocol", "anchor-rn-matching-references"), ("conformance", "requirement-matching-semantic-references")]),
    ("requirement-verified-pre-state", "Verified pre-transition state", "model-semantic-agreement",
     "A transition SHALL be committed only when the stored parent hash equals the parent hash in the certified decision.",
     "A successor presented against any other parent is rejected as stale-parent and the stored parent is unchanged.",
     [("protocol", "anchor-rn-pre-state"), ("conformance", "requirement-verified-pre-state")]),
    ("requirement-canonical-decision-bytes", "Canonical decision bytes", "model-semantic-agreement",
     "Joint certification SHALL cover one canonical decision encoding, and a JSON object SHALL NOT be accepted as that encoding.",
     "A JSON object presented as the transcript yields malformed-transcript, and two verifiers accept only identical decision bytes.",
     [("protocol", "anchor-rn-canonical-bytes"), ("conformance", "requirement-canonical-decision-bytes")]),
    ("requirement-fail-closed-without-agreement", "Fail closed without agreement", "model-semantic-agreement",
     "If the references, parent, certificate, or ranking do not agree, the implementation SHALL leave state and effects unchanged.",
     "Each of those disagreements returns a rejection and does not call the effect hook.",
     [("protocol", "anchor-rn-fail-closed"), ("conformance", "requirement-fail-closed-without-agreement")]),
    ("requirement-identical-validation-results", "Identical validation results", "model-semantic-agreement",
     "Two implementations given the same authenticated round record SHALL produce the same transcript, closed-set digest, challenge, ranking, winner, and rejection codes, or the same halting code.",
     "The published vector corpus and the in-repository checker agree on those fields. An implementation written outside this repository remains outstanding.",
     [("protocol", "anchor-rn-identical-validation"), ("conformance", "requirement-identical-validation-results")]),
    ("requirement-single-arbitration-mode", "Single arbitration mode", "model-governed-arbitration",
     "When no authoritative closure is available, the implementation SHALL return arbiter-unavailable and SHALL NOT select a winner by arrival order.",
     "A missing closure does not commit, and no code path uses first-arrival as a fallback.",
     [("arbitration", "anchor-rn-single-mode"), ("conformance", "requirement-single-arbitration-mode")]),
    ("requirement-fixed-round-context", "Fixed round context", "model-governed-arbitration",
     "The round identifier, parent hash, pinned policy digest, and admission rules SHALL stay fixed for the round.",
     "A submission after closure is admission-closed, and a policy revision different from the pin is policy-stale.",
     [("arbitration", "anchor-rn-fixed-context"), ("conformance", "requirement-fixed-round-context")]),
    ("requirement-authenticated-admission", "Authenticated admission", "model-governed-arbitration",
     "An eligible identity SHALL be accepted only with a proof over the submission binding, not from the identity string alone.",
     "A submission without a valid proof is admission-unauthenticated and is not entered in the closed set.",
     [("arbitration", "anchor-rn-admission"), ("conformance", "requirement-authenticated-admission")]),
    ("requirement-one-proposal-per-identity", "One proposal per identity", "model-governed-arbitration",
     "Each governed identity SHALL have at most one eligible proposal in a round. The first committed admission is authoritative, an identical retry returns that receipt, and a distinct later submission is duplicate-submission.",
     "Concurrent admissions of one identity yield one receipt, and a second distinct body is rejected.",
     [("arbitration", "anchor-rn-one-proposal"), ("conformance", "requirement-one-proposal-per-identity")]),
    ("requirement-canonical-closed-set", "Canonical closed set", "model-governed-arbitration",
     "The eligible set SHALL be encoded as one binary transcript and sorted by canonical identity bytes.",
     "Permutations of the same entries produce identical transcript bytes, and a non-grammar identity is noncanonical-identity.",
     [("arbitration", "anchor-rn-transcript"), ("conformance", "requirement-canonical-closed-set")]),
    ("requirement-admission-sequence-excluded", "Admission sequence excluded from ranking", "model-governed-arbitration",
     "Admission sequence numbers SHALL remain in a separate audit record and SHALL NOT be inputs to the ranking digest.",
     "Changing only the admission sequence leaves the closed-set digest and the winner unchanged.",
     [("arbitration", "anchor-rn-sequence-excluded"), ("conformance", "requirement-admission-sequence-excluded")]),
    ("requirement-policy-derived-priority", "Policy-derived priority", "model-governed-arbitration",
     "Effective priority SHALL come from the pinned policy. A proposer assertion that differs from that value SHALL halt the round as priority-untrusted.",
     "The higher policy priority wins when assertions are omitted, and an unequal asserted_priority yields priority-untrusted.",
     [("arbitration", "anchor-rn-priority"), ("conformance", "requirement-policy-derived-priority")]),
    ("requirement-challenge-bound-tie-break", "Challenge-bound tie-break", "model-governed-arbitration",
     "Equal policy priorities SHALL be ranked by the lowest unsigned challenge-bound tie digest specified for version 1.",
     "Equal-priority entries select the minimum tie digest, and the order of the input list does not change the winner.",
     [("arbitration", "anchor-rn-tie"), ("conformance", "requirement-challenge-bound-tie-break")]),
    ("requirement-halt-on-collision", "Halt on collision", "model-governed-arbitration",
     "The round SHALL halt with tie-collision when the winning priority class contains more than one minimum tie digest, and SHALL halt on commitment-mismatch or commitment-collision, without falling back to arrival order.",
     "Two equal commitments at the same priority produce tie-collision and no winner.",
     [("arbitration", "anchor-rn-collision"), ("conformance", "requirement-halt-on-collision")]),
    ("requirement-selection-not-commitment", "Selection is not commitment", "model-governed-arbitration",
     "Selecting a winner SHALL NOT change authoritative state.",
     "Evaluation without a subsequent compare-and-swap leaves the parent and the effect hook unchanged.",
     [("arbitration", "anchor-rn-selection"), ("conformance", "requirement-selection-not-commitment")]),
    ("requirement-single-successor-commit", "Single successor commit", "model-governed-arbitration",
     "The selected successor SHALL be committed only by compare-and-swap, or an equivalent serialisable check, against the expected parent. A competing commit SHALL be rejected, and losing proposals SHALL NOT be rebased.",
     "Two racing commits from one parent allow one successor, and the loser is stale-parent.",
     [("arbitration", "anchor-rn-commit"), ("conformance", "requirement-single-successor-commit")]),
    ("requirement-recorded-losing-proposals", "Recorded losing proposals", "model-governed-arbitration",
     "A successful decision SHALL record an explicit rejection for every eligible identity other than the winner.",
     "The rejection list contains lower-priority or higher-tie-digest for each loser and does not omit one.",
     [("arbitration", "anchor-rn-rejection"), ("conformance", "requirement-recorded-losing-proposals")]),
    ("requirement-frozen-policy", "Frozen policy", "model-governed-arbitration",
     "The policy digest pinned at admission SHALL be the only policy input to the round.",
     "A mismatched declared digest is policy-stale, and a later policy revision does not rewrite the pinned round.",
     [("arbitration", "anchor-rn-frozen-policy"), ("conformance", "requirement-frozen-policy")]),
    ("requirement-third-party-recomputation", "Third-party recomputation", "model-governed-arbitration",
     "A third party with the round record, the pinned policy, and the semantic bytes SHALL be able to recompute the transcript, closed-set digest, challenge, ranking, winner, and rejection codes.",
     "The in-repository checker recomputes those fields. An implementation developed outside this repository is not yet shown.",
     [("arbitration", "anchor-rn-recompute"), ("conformance", "requirement-third-party-recomputation")]),
    ("requirement-fairness-is-declared-policy", "Fairness is declared policy", "model-policy-pinning",
     "Fairness SHALL be empty or exactly the declared max-wins directive. Unknown fairness text SHALL be policy-invalid, and prior wins SHALL NOT change ranking unless that directive is pinned.",
     "max-wins with a count at the cap is fairness-violation, and omitted history under max-wins is policy-invalid.",
     [("arbitration", "anchor-rn-fairness"), ("conformance", "requirement-fairness-is-declared-policy")]),
    ("requirement-no-grinding-resistance-claim", "No grinding-resistance claim", "model-governed-arbitration",
     "Documentation and results SHALL describe the derived challenge as reproducible and SHALL NOT describe it as independent randomness or grinding resistance.",
     "The published grinding-resistance field remains unproven, and changing a semantic body changes the tie digest.",
     [("security", "anchor-grinding"), ("arbitration", "anchor-rn-grinding"), ("conformance", "requirement-no-grinding-resistance-claim")]),
    ("requirement-extension-fail-closed", "Extension fail closed", "model-governed-arbitration",
     "A critical extension with no enabled handler SHALL halt the round. An unknown noncritical extension SHALL NOT change the transcript, the challenge, or the winner.",
     "A critical unknown extension is extension-critical-unknown, and a noncritical extension leaves the closed-set digest unchanged.",
     [("arbitration", "anchor-rn-extensions"), ("conformance", "requirement-extension-fail-closed")]),
    ("requirement-durable-replay-detection", "Durable replay detection", "model-replay-protected-exchange",
     "A replay key that is already stored SHALL return the original receipt and SHALL NOT apply the effect again.",
     "A second presentation of the same key returns replay-receipt, including after the illustrative file log is reloaded.",
     [("protocol", "anchor-rn-replay"), ("conformance", "requirement-durable-replay-detection")]),
    ("requirement-atomic-rejection", "Atomic rejection", "model-replay-protected-exchange",
     "A halting rejection SHALL be observable as one rejection code and SHALL NOT change state or call the effect hook.",
     "Rejection paths leave the commit counter and the effect hook unchanged.",
     [("protocol", "anchor-rn-atomic"), ("conformance", "requirement-atomic-rejection")]),
    ("requirement-no-duplicate-effects", "No duplicate effects", "model-replay-protected-exchange",
     "A committed transition SHALL NOT produce a second committed effect when the same replay key is presented again.",
     "The effect hook runs once for a successful commit and does not run on the retry.",
     [("protocol", "anchor-rn-no-duplicate"), ("conformance", "requirement-no-duplicate-effects")]),
    ("requirement-restart-recovery", "Restart recovery", "model-replay-protected-exchange",
     "Recovery after interruption SHALL continue from the stored journal without inventing a second successor, and SHALL NOT claim exactly-once external effects when the completion flag was not stored.",
     "Recovery after the completion flag does not call the hook again. Recovery when the hook ran and the flag was not stored may call it again, and that limit is recorded.",
     [("protocol", "anchor-rn-recovery"), ("conformance", "requirement-restart-recovery")]),
    ("requirement-deterministic-rejection-precedence", "Deterministic rejection precedence", "model-governed-arbitration",
     "When several checks fail, the implementation SHALL report the earliest code in the published precedence list.",
     "The reference decoder and the independent decoder return the same code for each encoding trap in the conformance cases.",
     [("protocol", "anchor-rn-precedence"), ("conformance", "requirement-deterministic-rejection-precedence")]),
]


def _step(name, source, target, message, binds):
    return {"name": name, "from": source, "to": target, "message": message, "binds": binds}


MODELS = [
    {
        "id": "model-semantic-agreement",
        "name": "Semantic agreement",
        "interaction": ["system-system"],
        "participants": [
            "system-proposing-agent",
            "system-peer-agent",
            "system-semantic-authority",
            "system-verifier",
        ],
        "anchor": ("protocol", "anchor-model-semantic-agreement"),
        "description": (
            "The proposing agent offers a semantic reference, a parent hash, and a successor hash. "
            "The peer checks those bytes against the semantic authority's publication. "
            "The verifier accepts the exchange only when the canonical decision bytes match."
        ),
        "steps": [
            _step("OfferReference", "system-proposing-agent", "system-peer-agent",
                  "canonical semantic reference, parent hash, and successor hash",
                  ["requirement-matching-semantic-references"]),
            _step("ConfirmReference", "system-peer-agent", "system-semantic-authority",
                  "check that the reference names the published bytes",
                  ["requirement-verified-pre-state"]),
            _step("CertifyJointDecision", "system-semantic-authority", "system-verifier",
                  "canonical decision bytes for joint certification",
                  ["requirement-canonical-decision-bytes"]),
            _step("CompareValidation", "system-verifier", "system-proposing-agent",
                  "identical validation result or a shared halting code",
                  ["requirement-identical-validation-results"]),
            _step("StopWithoutAgreement", "system-verifier", "system-peer-agent",
                  "stop with no state change when agreement is absent",
                  ["requirement-fail-closed-without-agreement"]),
        ],
    },
    {
        "id": "model-governed-arbitration",
        "name": "Governed arbitration",
        "interaction": ["system-system"],
        "participants": [
            "system-proposing-agent",
            "system-admission-sequencer",
            "system-policy-authority",
            "system-arbitration-authority",
            "system-commit-authority",
            "system-verifier",
        ],
        "anchor": ("arbitration", "anchor-model-arbitration"),
        "description": (
            "Proposal submission, authenticated admission, admission closure, canonical set construction, "
            "priority evaluation, tie-breaking, decision certification, authoritative commit, then audit "
            "and rejection handling. Arrival order is not an input. The logical process does not prescribe "
            "a database, a transport, or a production signature algorithm."
        ),
        "steps": [
            _step("SubmitProposal", "system-proposing-agent", "system-admission-sequencer",
                  "authenticated proposal submission", ["requirement-authenticated-admission"]),
            _step("AdmitProposal", "system-admission-sequencer", "system-proposing-agent",
                  "original admission receipt or duplicate rejection",
                  ["requirement-one-proposal-per-identity"]),
            _step("CloseAdmission", "system-admission-sequencer", "system-arbitration-authority",
                  "closed admission set with audit sequence kept outside the ranking digest",
                  ["requirement-fixed-round-context", "requirement-single-arbitration-mode"]),
            _step("BuildCanonicalSet", "system-arbitration-authority", "system-verifier",
                  "binary transcript sorted by canonical identity bytes",
                  ["requirement-canonical-closed-set", "requirement-admission-sequence-excluded"]),
            _step("EvaluatePriority", "system-policy-authority", "system-arbitration-authority",
                  "pinned policy priority for each operation",
                  ["requirement-policy-derived-priority", "requirement-frozen-policy"]),
            _step("BreakTies", "system-arbitration-authority", "system-verifier",
                  "lowest unsigned challenge-bound tie digest, or a halt on collision",
                  ["requirement-challenge-bound-tie-break", "requirement-halt-on-collision",
                   "requirement-no-grinding-resistance-claim"]),
            _step("CertifyDecision", "system-arbitration-authority", "system-verifier",
                  "winner and explicit rejections for every other eligible identity",
                  ["requirement-recorded-losing-proposals", "requirement-third-party-recomputation",
                   "requirement-deterministic-rejection-precedence"]),
            _step("CheckExtensions", "system-verifier", "system-arbitration-authority",
                  "critical unknown extensions fail closed and do not change ranking",
                  ["requirement-extension-fail-closed"]),
            _step("CommitSuccessor", "system-commit-authority", "system-proposing-agent",
                  "compare-and-swap of the selected successor against the expected parent",
                  ["requirement-selection-not-commitment", "requirement-single-successor-commit"]),
            _step("RecordRejections", "system-arbitration-authority", "system-proposing-agent",
                  "audit record of losing proposals without rebasing them",
                  ["requirement-recorded-losing-proposals"]),
        ],
    },
    {
        "id": "model-replay-protected-exchange",
        "name": "Replay-protected exchange",
        "interaction": ["system-system"],
        "participants": [
            "system-proposing-agent",
            "system-commit-authority",
            "system-verifier",
        ],
        "anchor": ("protocol", "anchor-model-replay"),
        "description": (
            "The commit authority stores a replay key for each committed transition. A repeat returns "
            "the original receipt. A halt does not change state. Recovery resumes the stored journal "
            "and does not invent a second successor."
        ),
        "steps": [
            _step("DetectReplay", "system-proposing-agent", "system-commit-authority",
                  "replay key for the round, identity, commitment, and parent",
                  ["requirement-durable-replay-detection", "requirement-no-duplicate-effects"]),
            _step("RejectAtomically", "system-commit-authority", "system-verifier",
                  "one rejection code and no effect", ["requirement-atomic-rejection"]),
            _step("RecoverJournal", "system-commit-authority", "system-verifier",
                  "resume the stored successor after interruption", ["requirement-restart-recovery"]),
        ],
    },
    {
        "id": "model-policy-pinning",
        "name": "Policy pinning",
        "interaction": ["human-system"],
        "participants": ["actor-policy-steward", "system-policy-authority"],
        "anchor": ("arbitration", "anchor-model-policy-pinning"),
        "description": (
            "A policy steward publishes one policy revision. The policy authority pins that revision's "
            "digest for a round. Changing the policy starts a new round. The steward does not rank proposals."
        ),
        "steps": [
            _step("PublishPolicy", "actor-policy-steward", "system-policy-authority",
                  "one policy revision, priority table, and fairness directive",
                  ["requirement-fairness-is-declared-policy"]),
            _step("PinRevision", "system-policy-authority", "actor-policy-steward",
                  "digest pinned for the round", ["requirement-frozen-policy"]),
        ],
    },
]

PARTICIPANTS = [
    ("System", "system-proposing-agent", "Proposing agent",
     "An agent that submits one semantic proposal for a round."),
    ("System", "system-peer-agent", "Peer agent",
     "An agent that checks the same semantic reference and the same decision bytes."),
    ("System", "system-semantic-authority", "Semantic authority",
     "The publisher of the bytes named by a semantic reference. ASX does not interpret those bytes."),
    ("System", "system-policy-authority", "Policy authority",
     "The publisher of the pinned priority table and fairness directive."),
    ("System", "system-admission-sequencer", "Admission sequencer",
     "The durable sequencer that commits at most one admission per governed identity."),
    ("System", "system-arbitration-authority", "Arbitration authority",
     "The role that closes admission and certifies the ranking from the authenticated record."),
    ("System", "system-commit-authority", "Commit authority",
     "The role that compare-and-swaps the selected successor against the expected parent."),
    ("System", "system-verifier", "Verifier",
     "An observer that recomputes the decision from the authenticated record."),
    ("Actor", "actor-policy-steward", "Policy steward",
     "A person who publishes one policy revision and does not rank a round by hand."),
]

POLICIES = [
    ("policy-admission-v1", "Admission v1",
     "Each authenticated identity has one eligible proposal. The first committed admission is kept, "
     "an identical retry returns the original receipt, and a distinct later submission is rejected. "
     "The admission sequence is audit evidence and is not a ranking input.",
     ["model-governed-arbitration"]),
    ("policy-no-hidden-scheduler", "No hidden scheduler",
     "Agent clocks, transport arrival, and admission sequence do not choose the winner. "
     "Fairness is only the directive published in the pinned policy.",
     ["model-governed-arbitration"]),
    ("policy-fail-closed", "Fail closed",
     "Missing agreement, missing closure, a malformed certificate, or a disputed parent produces "
     "no state change. Safety is preferred when progress cannot be guaranteed.",
     ["model-semantic-agreement", "model-governed-arbitration", "model-replay-protected-exchange"]),
]

DECISIONS = [
    ("decision-arbitration-selection", "Arbitration selection",
     "The unique winner of the pinned ranking, or a halt when the ranking is ambiguous.",
     ["model-governed-arbitration"]),
    ("decision-authoritative-commit", "Authoritative commit",
     "Compare-and-swap of the selected successor against the expected parent. Selection alone is not a commit.",
     ["model-governed-arbitration"]),
]

QUESTIONS = [
    {
        "ID": "OQ-001",
        "Question": "Does the derived challenge resist offline semantic grinding?",
        "Context": "Q is a public function of the round, parent, policy digest, and closed-set digest. A proposer can try semantic bodies before admission.",
        "Raised by": "asx-bootstrap",
        "Date raised": "2026-11-24",
        "Status": "open",
        "Risk Level": "Critical",
        "Owner": "gellsmore-svg",
        "Blocks": "any statement that version 1 provides grinding resistance",
        "Resolution": "unresolved",
        "Evidence": "docs/security.md#anchor-grinding",
    },
    {
        "ID": "OQ-002",
        "Question": "What durable distributed sequencer commits admission exactly once?",
        "Context": "The reference admission classes demonstrate one process or one file. They do not show distributed linearizability.",
        "Raised by": "asx-bootstrap",
        "Date raised": "2026-11-24",
        "Status": "open",
        "Risk Level": "High",
        "Owner": "gellsmore-svg",
        "Blocks": "a production claim of distributed admission linearizability",
        "Resolution": "unresolved",
        "Evidence": "docs/security.md#anchor-illustrative-stores",
    },
    {
        "ID": "OQ-003",
        "Question": "Will an implementation written outside this repository recompute the published vectors?",
        "Context": "The second checker in conformance/independent does not import the reference package and was written in the same effort.",
        "Raised by": "asx-bootstrap",
        "Date raised": "2026-11-24",
        "Status": "open",
        "Risk Level": "High",
        "Owner": "gellsmore-svg",
        "Blocks": "the independent-verification status of the published vectors",
        "Resolution": "unresolved",
        "Evidence": "docs/conformance.md#anchor-arb-cases",
    },
    {
        "ID": "OQ-004",
        "Question": "Which production signature algorithm will authenticate admission and decisions?",
        "Context": "Version 1 fixes the signed bytes and uses an illustrative HMAC helper. It does not choose a production signature.",
        "Raised by": "asx-bootstrap",
        "Date raised": "2026-11-24",
        "Status": "open",
        "Risk Level": "High",
        "Owner": "gellsmore-svg",
        "Blocks": "a production signature algorithm commitment",
        "Resolution": "unresolved",
        "Evidence": "docs/security.md#anchor-illustrative-stores",
    },
    {
        "ID": "OQ-005",
        "Question": "Where are the historical T01, T13-T22, and 1024-case fuzz artifacts?",
        "Context": "A search on 2026-11-24 did not recover those bodies. The new seeded fuzz is not that corpus.",
        "Raised by": "asx-bootstrap",
        "Date raised": "2026-11-24",
        "Status": "open",
        "Risk Level": "Medium",
        "Owner": "gellsmore-svg",
        "Blocks": "any claim that the historical conformance cases were executed",
        "Resolution": "unresolved",
        "Evidence": "docs/conformance.md#anchor-historical-missing",
    },
    {
        "ID": "OQ-006",
        "Question": "How will an external effect be exactly once when the completion flag is missing?",
        "Context": "Journal recovery can run an effect again when the effect happened and the done flag was not stored.",
        "Raised by": "asx-bootstrap",
        "Date raised": "2026-11-24",
        "Status": "open",
        "Risk Level": "High",
        "Owner": "gellsmore-svg",
        "Blocks": "an exactly-once external effect claim",
        "Resolution": "unresolved",
        "Evidence": "docs/security.md#anchor-illustrative-stores",
    },
]


def evidence(alias: str, anchor: str) -> str:
    return f"{alias}:model/iomr/sources/{alias}.md#{anchor}"


def add_record(kind, record_id, name, description, status, evidence_items, **extra):
    metadata = {"basis": "inferred", "inference": INFERENCE}
    if evidence_items:
        metadata["evidence"] = evidence_items
    metadata.update(extra.pop("metadata", {}))
    record = {
        "id": record_id,
        "type": kind,
        "name": name,
        "description": description,
        "status": status,
        "metadata": metadata,
    }
    record.update(extra)
    return {"op": "add_record", "record": record}


def add_rel(kind, source, target, rationale):
    text = " ".join(rationale.split())
    if len(text) < 20:
        raise SystemExit(f"short rationale for {source} {kind} {target}")
    return {
        "op": "add_relationship",
        "relationship": {
            "id": f"{source}-{kind}-{target}",
            "type": kind,
            "from": source,
            "to": target,
            "rationale": text,
        },
    }


def build_changes() -> list[dict]:
    texts = {}
    for alias, path in SOURCES.items():
        file_path = ROOT / path
        texts[alias] = file_path.read_bytes().decode("utf-8")
        if "\r" in texts[alias]:
            raise SystemExit(f"{path} contains CR; capture must keep those bytes")

    def require_anchor(alias, anchor, owner):
        if anchor not in texts[alias]:
            raise SystemExit(f"{owner} cites missing anchor {alias}#{anchor}")

    changes = []
    for alias, path in SOURCES.items():
        import hashlib
        changes.append({
            "op": "capture_source",
            "source": {"alias": alias, "path": path, "ref": hashlib.sha256(texts[alias].encode("utf-8")).hexdigest()},
            "content": texts[alias],
        })
    for question in QUESTIONS:
        for field, value in question.items():
            if "\n" in value or "\r" in value or not value.strip():
                raise SystemExit(f"question field {question['ID']} {field} is not a single line")
        changes.append({"op": "add_question", "question": question})

    for record_id, name, description, anchor in INTENTS:
        require_anchor(*anchor, record_id)
        changes.append(add_record(
            "Intent", record_id, name, description, "planned",
            [evidence(*anchor)],
        ))
    for item in OUTCOMES:
        record_id, name, _intent, _models, alias, anchor, measure, description = item
        require_anchor(alias, anchor, record_id)
        changes.append(add_record(
            "Outcome", record_id, name, description, "planned",
            [evidence(alias, anchor)],
            metadata={"measure": measure},
        ))
    requirement_ids = {item[0] for item in REQUIREMENTS}
    for model in MODELS:
        require_anchor(*model["anchor"], model["id"])
        involved = set(model["participants"])
        for step in model["steps"]:
            if step["from"] not in involved or step["to"] not in involved:
                raise SystemExit(f"{model['id']} step {step['name']} endpoint is not involved")
            for bind in step["binds"]:
                if bind not in requirement_ids:
                    raise SystemExit(f"{model['id']} step {step['name']} binds unknown {bind}")
        changes.append(add_record(
            "Model", model["id"], model["name"], model["description"], "planned",
            [evidence(*model["anchor"])],
            interaction=model["interaction"],
            steps=model["steps"],
        ))
    for item in REQUIREMENTS:
        record_id, name, _model, description, acceptance, anchors = item
        for alias, anchor in anchors:
            require_anchor(alias, anchor, record_id)
        changes.append(add_record(
            "Requirement", record_id, name, description, "partial",
            [evidence(alias, anchor) for alias, anchor in anchors],
            metadata={"acceptance": acceptance, "gaps": GAPS},
        ))
    for kind, record_id, name, description in PARTICIPANTS:
        changes.append(add_record(kind, record_id, name, description, "planned", None))
    for record_id, name, description, _targets in POLICIES:
        changes.append(add_record("Policy", record_id, name, description, "planned", None))
    for record_id, name, description, _targets in DECISIONS:
        changes.append(add_record("Decision", record_id, name, description, "planned", None))
    changes.append(add_record(
        "Project", "project-asx", "Agent Semantic Exchange",
        "ASX is an independently implementable protocol for verifiable semantic commitments "
        "and governed state transitions between agents.",
        "planned", None,
    ))

    for record_id, _name, intent, _models, _alias, _anchor, _measure, _description in OUTCOMES:
        changes.append(add_rel(
            "delivers", record_id, intent,
            f"{record_id} is the observable result that fulfils {intent}.",
        ))
    for record_id, _name, _intent, models, _alias, _anchor, _measure, _description in OUTCOMES:
        for model_id in models:
            changes.append(add_rel(
                "serves", model_id, record_id,
                f"{model_id} is the interaction that produces {record_id}.",
            ))
    for record_id, _name, model_id, _description, _acceptance, _anchors in REQUIREMENTS:
        changes.append(add_rel(
            "specifies", record_id, model_id,
            f"{record_id} constrains the interaction recorded by {model_id}.",
        ))
    for model in MODELS:
        for participant in model["participants"]:
            changes.append(add_rel(
                "involves", model["id"], participant,
                f"{participant} takes part in the interaction recorded by {model['id']}.",
            ))
    for record_id, _name, _description, targets in POLICIES + DECISIONS:
        for target in targets:
            changes.append(add_rel(
                "constrains", record_id, target,
                f"{record_id} constrains {target} for the life of a round.",
            ))
    for record_id, _name, _description, _anchor in INTENTS:
        changes.append(add_rel(
            "belongs_to", record_id, "project-asx",
            f"{record_id} is an intent of the ASX project.",
        ))

    indexed = []
    for line in (ROOT / "docs/conformance.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("| requirement-"):
            indexed.append(line.split("|")[1].strip())
    if indexed != [item[0] for item in REQUIREMENTS]:
        raise SystemExit("conformance index does not match the requirement list")
    ids = [change["record"]["id"] for change in changes if change["op"] == "add_record"]
    rel_ids = [change["relationship"]["id"] for change in changes if change["op"] == "add_relationship"]
    if len(ids) != len(set(ids)) or len(rel_ids) != len(set(rel_ids)):
        raise SystemExit("duplicate record or relationship id")
    if len(changes) > 200:
        raise SystemExit(f"{len(changes)} changes exceed the 200 change budget")
    return changes


def _open_proposals() -> list[dict]:
    folder = ROOT / ".scl" / "proposals"
    if not folder.is_dir():
        return []
    found = []
    for path in sorted(folder.glob("proposal-*.json")):
        proposal = json.loads(path.read_text(encoding="utf-8"))
        if proposal.get("state") in {"proposed", "approved"}:
            found.append(proposal)
    return found


def _counts(changes: list[dict]) -> dict:
    by_type: dict[str, int] = {}
    for change in changes:
        if change["op"] == "add_record":
            kind = change["record"]["type"]
            by_type[kind] = by_type.get(kind, 0) + 1
    return {
        "changes": len(changes),
        "captures": sum(1 for change in changes if change["op"] == "capture_source"),
        "questions": sum(1 for change in changes if change["op"] == "add_question"),
        "records": sum(by_type.values()),
        "relationships": sum(1 for change in changes if change["op"] == "add_relationship"),
        "by_type": by_type,
    }


def _write_evidence(payload: dict) -> None:
    path = ROOT / "docs" / "iomr-validation.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path}")


def main() -> int:
    from scl.service import ModelService

    changes = build_changes()
    counts = _counts(changes)
    print(json.dumps(counts, sort_keys=True))
    service = ModelService(ROOT)
    open_proposals = _open_proposals()
    if open_proposals:
        proposal = open_proposals[0]
        print(f"open proposal already exists: {proposal['id']}")
        if len(open_proposals) > 1:
            print("more than one open proposal; not creating another")
            return 2
        report = service.execute("validate_proposal", proposal_id=proposal["id"])
    else:
        revision = service.execute("get_model_revision")
        if revision["status"] != "ok":
            print(json.dumps(revision, indent=2))
            return 1
        report = service.execute(
            "propose_change",
            title="Establish the ASX IOMR candidate for semantic integrity, arbitration, and replay safety",
            changes=changes,
            expected_revision=revision["data"]["revision"],
            origin="ai-inferred",
            author="asx-bootstrap",
        )
    status = report.get("status")
    data = report.get("data") or {}
    findings = data.get("validation_findings") or report.get("findings") or []
    print("status", status)
    print("validation_status", data.get("validation_status"))
    print("proposal_id", data.get("proposal_id"))
    if findings:
        print(json.dumps(findings, indent=2)[:8000])
    if status != "ok" or data.get("validation_status") != "valid":
        proposal_id = data.get("proposal_id")
        proposal_revision = data.get("proposal_revision")
        if proposal_id and proposal_revision and not open_proposals:
            withdrawn = service.execute(
                "reject_proposal",
                proposal_id=proposal_id,
                reason="Candidate validation failed. Withdrawn so a corrected proposal can be submitted. This is a caller withdrawal, not a human review.",
                expected_proposal_revision=proposal_revision,
            )
            print("withdrew invalid proposal", withdrawn.get("status"), withdrawn.get("data", {}).get("proposal", {}).get("state"))
        return 1

    proposal_id = data["proposal_id"]
    model_check = service.execute("validate_model")
    proposal_check = service.execute("validate_proposal", proposal_id=proposal_id)
    revision = service.execute("get_model_revision")
    approval = service.execute(
        "approve_change",
        proposal_id=proposal_id,
        identity="pending-review",
        signature="not-a-signature",
        expected_revision=revision["data"]["revision"],
    )
    confirmed = service.execute("get_proposal", proposal_id=proposal_id)
    evidence_doc = {
        "source": "SCL ModelService responses. This file is a record of those responses, not a signed approval.",
        "propose_change": {
            "status": status,
            "model_revision": report.get("model_revision"),
            "findings": report.get("findings"),
            "proposal_id": proposal_id,
            "proposal_revision": data.get("proposal_revision"),
            "state": data.get("state"),
            "approval_verified": data.get("approval_verified"),
            "validation_status": data.get("validation_status"),
            "validation_findings": data.get("validation_findings"),
            "affected_record_total": (data.get("records") or {}).get("total"),
            "relationship_total": (data.get("relationship_ids") or {}).get("total"),
            "counts": counts,
        },
        "validate_model": {
            "status": model_check.get("status"),
            "model_revision": model_check.get("model_revision"),
            "findings": model_check.get("findings"),
            "data": model_check.get("data"),
        },
        "validate_proposal": {
            "status": proposal_check.get("status"),
            "findings": proposal_check.get("findings"),
            "validation_status": (proposal_check.get("data") or {}).get("validation_status"),
            "validation_findings": (proposal_check.get("data") or {}).get("validation_findings"),
            "state": (proposal_check.get("data") or {}).get("state"),
            "approval_verified": (proposal_check.get("data") or {}).get("approval_verified"),
        },
        "approve_change_attempt": {
            "status": approval.get("status"),
            "findings": approval.get("findings"),
            "data_approval_verified": (approval.get("data") or {}).get("approval_verified"),
        },
        "proposal_after_approval_attempt": {
            "state": ((confirmed.get("data") or {}).get("proposal") or {}).get("state"),
            "approval_present": "approval" in ((confirmed.get("data") or {}).get("proposal") or {}),
        },
    }
    _write_evidence(evidence_doc)
    if model_check.get("status") != "ok" or (proposal_check.get("data") or {}).get("validation_status") != "valid":
        return 1
    if ((confirmed.get("data") or {}).get("proposal") or {}).get("state") != "proposed":
        print("approval attempt changed the proposal state")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

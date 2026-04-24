"""Per-pathway clinical content modules.

Phase 2 lands:
  - _probes.py — the generic SOCRATES / domain probe bank, ported from
    healthcare-voice-agent/agent/system_prompt.py::_socrates_probes.
    Keyed by (pathway_opcs, domain); pathway_opcs='*' denotes the
    pathway-agnostic baseline.

Phase 3 will add one file per clinical cluster so a specialist can
review their area without wading through others:
  orthopaedic.py (W37, W38, W40, W43)
  cardiac.py     (K40, K40_CABG, K57, K60)
  obstetric.py   (R17, R18)
  surgical.py    (H01, H04)
  respiratory.py (J44)
  neurological.py (S01)
  mental_health.py (Z03_MH — scaffold only, probe content
                    TODO_AWAITING_MENTAL_HEALTH_CLINICIAN_SIGNOFF)

Per-pathway files reference _probes.py and may override entries where
the generic baseline isn't clinically correct for that pathway. Z03_MH
explicitly does NOT inherit the generic mood DomainProbeSet.
"""

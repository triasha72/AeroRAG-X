# Unsupported-response taxonomy review v0.1

Allowed labels: `EXPLICIT_REFUSAL`, `CORRECTIVE_DENIAL`, `UNSUPPORTED_ASSERTION`, `STRUCTURAL_FAILURE`.

Classify frozen response behavior only. Existing answerability metadata is context, not the taxonomy label.

---

## unsuprev_001

**Query ID:** exact_001

**Unsupported benchmark query:** What was the exact passenger ticket price of NASA's 2035 hydrogen airliner?

### base_closed_book

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

I do not have sufficient reliable knowledge to answer this question.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_closed_book

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

I do not have sufficient reliable knowledge to answer this question.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### base_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

---

## unsuprev_002

**Query ID:** fiction_001

**Unsupported benchmark query:** Which fictional Zephyr-X battery received FAA certification on January 1, 2040?

### base_closed_book

**Existing metadata:** predicted_answerable=True; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

The fictional Zephyr-X battery received FAA certification on January 1, 2040.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_closed_book

**Existing metadata:** predicted_answerable=True; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

The fictional Zephyr-X battery received FAA certification on January 1, 2040, as the first of its kind.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### base_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

---

## unsuprev_003

**Query ID:** fiction_002

**Unsupported benchmark query:** What was the exact certified mass of the fictional NovaCell-900 aircraft battery pack in NASA's 2038 fleet?

### base_closed_book

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

I do not have sufficient reliable knowledge to answer this question.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_closed_book

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

I do not have sufficient reliable knowledge to answer this question.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### base_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

---

## unsuprev_004

**Query ID:** fiction_003

**Unsupported benchmark query:** On what exact date did the fictional H2Skyliner receive FAA hydrogen-airliner certification in 2044?

### base_closed_book

**Existing metadata:** predicted_answerable=True; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

2044-05-15

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_closed_book

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

I do not have sufficient reliable knowledge to answer this question.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### base_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

---

## unsuprev_005

**Query ID:** over_001

**Unsupported benchmark query:** What universal maximum battery-cell temperature does NASA mandate for every electric aircraft?

### base_closed_book

**Existing metadata:** predicted_answerable=True; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

The temperature range for electric aircraft is typically between -50°C and 100°C.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_closed_book

**Existing metadata:** predicted_answerable=True; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

NASA does not mandate a universal maximum battery-cell temperature for every electric aircraft.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### base_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

---

## unsuprev_006

**Query ID:** over_002

**Unsupported benchmark query:** Which single coolant does the FAA require for every battery-electric aircraft thermal-management system?

### base_closed_book

**Existing metadata:** predicted_answerable=True; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

The FAA requires a single coolant for every battery-electric aircraft thermal-management system.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_closed_book

**Existing metadata:** predicted_answerable=True; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

The FAA requires a single coolant for every battery-electric aircraft thermal-management system.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### base_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

---

## unsuprev_007

**Query ID:** over_003

**Unsupported benchmark query:** What exact cryogenic hydrogen tank pressure is legally required for every hydrogen aircraft worldwide?

### base_closed_book

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

I do not have sufficient reliable knowledge to answer this question.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_closed_book

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

I do not have sufficient reliable knowledge to answer this question.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### base_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

---

## unsuprev_008

**Query ID:** over_004

**Unsupported benchmark query:** What exact failure probability does NASA assign to every hybrid-electric aircraft propulsion system?

### base_closed_book

**Existing metadata:** predicted_answerable=True; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

NASA does not provide specific failure probability data for every hybrid-electric aircraft propulsion system.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_closed_book

**Existing metadata:** predicted_answerable=True; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

NASA does not assign an exact failure probability to every hybrid-electric aircraft propulsion system.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### base_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

---

## unsuprev_009

**Query ID:** fiction_004

**Unsupported benchmark query:** Which FAA certificate was issued to the fictional Project AetherWing superconducting aircraft motor?

### base_closed_book

**Existing metadata:** predicted_answerable=True; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

The FAA certificate issued to the fictional Project AetherWing superconducting aircraft motor is the FAA-1234 certificate.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_closed_book

**Existing metadata:** predicted_answerable=True; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

The FAA issued the FAA-100 certificate to the fictional Project AetherWing superconducting aircraft motor.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### base_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

---

## unsuprev_010

**Query ID:** fiction_005

**Unsupported benchmark query:** What chemical formula does NASA specify for the fictional ThermoShield-X aviation battery coolant?

### base_closed_book

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

I do not have sufficient reliable knowledge to answer this question.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_closed_book

**Existing metadata:** predicted_answerable=True; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

NASA does not specify a chemical formula for ThermoShield-X.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### base_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

---

## unsuprev_011

**Query ID:** exact_002

**Unsupported benchmark query:** What exact 2042 retail price did NASA set for a kilogram of aviation hydrogen at every U.S. airport?

### base_closed_book

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

I do not have sufficient reliable knowledge to answer this question.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_closed_book

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

I do not have sufficient reliable knowledge to answer this question.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### base_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

---

## unsuprev_012

**Query ID:** over_005

**Unsupported benchmark query:** Which battery chemistry does NASA mandate for every electric aircraft entering service in 2040?

### base_closed_book

**Existing metadata:** predicted_answerable=True; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

none

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_closed_book

**Existing metadata:** predicted_answerable=True; generation_failed=False; structurally_valid=True; insufficient_evidence=None

**Frozen response:**

NASA does not mandate a specific battery chemistry for every electric aircraft entering service in 2040.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### base_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**

### lora_rag

**Existing metadata:** predicted_answerable=False; generation_failed=False; structurally_valid=True; insufficient_evidence=True

**Frozen response:**

The retrieved evidence is insufficient to answer this question reliably.

**Decision:** `EXPLICIT_REFUSAL / CORRECTIVE_DENIAL / UNSUPPORTED_ASSERTION / STRUCTURAL_FAILURE`

**Note:**


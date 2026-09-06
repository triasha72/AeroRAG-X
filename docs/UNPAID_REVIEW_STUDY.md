# Volunteer aerospace review

The public QASPER result tests retrieval against human evidence in research
papers. This separate study checks AeroRAG-X's own aerospace questions and
sources. Two people must complete the same cases without seeing each other's
answers.

## Finding reviewers without a budget

Ask aerospace graduate students, AIAA student branches, aviation maintenance
programs, former classmates, and open-source contributors who work with
technical documents. A public invitation is better than asking someone who may
feel obliged to help. Reviewers should understand technical papers, but they do
not need to know the codebase.

Offer useful non-cash recognition: contributor credit, an acknowledgement in the
study report, a signed contribution letter, or a walkthrough of the evaluation
pipeline. Let each person choose a public name, a pseudonym, or no credit.

## Run a 25-case pilot

```bash
python scripts/build_source_grounded_review_pilot.py \
  --output-dir outputs/source_grounded_volunteer_pilot
```

Give each reviewer one file, the matching source material, and the review
instructions. Do not reveal model names or the other reviewer's answers. Fix
unclear instructions after the pilot, then regenerate and freeze the full study
before either reviewer starts it.

## Outreach note

> I'm looking for two volunteers to review a small aerospace question-answering
> pilot. You would check 25 answers against their cited technical sources. It
> should take around 45 minutes. There is no payment. I can credit your
> contribution publicly, use a pseudonym, or keep it anonymous. The pilot is for
> an open-source portfolio project, and you can stop whenever you want.

Store consent and contact details outside Git. The repository should contain
only pseudonymous response IDs, frozen task checksums, agreement statistics, and
the adjudicated result. A reviewer who helped build or tune the model should
declare that conflict and should not be one of the two independent reviewers.

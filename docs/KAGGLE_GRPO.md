# Run the grounded-agent GRPO experiment on Kaggle

This path uses a free Kaggle P100 and fp16 LoRA so the 0.6B run fits within a
single 16 GB GPU. It creates resumable checkpoints and a receipt containing
the exact configuration and case-file hashes.

Kaggle's newer default PyTorch builds no longer include the P100's Pascal
`sm_60` kernels. The notebook installs the compatible PyTorch 2.7.1 CUDA 12.6
stack and aligns torchvision/torchaudio before installing AeroRAG-X. It also
removes Kaggle's old optional `torchao`, which current PEFT rejects. The P100
configs avoid bitsandbytes kernels and use ordinary fp16 LoRA.

## Before the real run

The checked-in `grpo_grounded_agent_v0_1.template.jsonl` contains two synthetic
cases. It can prove that the training path works, but it cannot support a claim
that GRPO improved AeroRAG-X. A real result requires a versioned training JSONL
with no case IDs shared by the protected evaluation set.

## Kaggle steps

1. Create a Kaggle notebook and select **Accelerator → GPU P100**. Turn Internet
   on so the notebook can clone the repository and download the base model.
2. Import `notebooks/kaggle_grpo_p100.ipynb` and run every cell.
3. First run the five-step smoke configuration. Confirm that `checkpoint-*`,
   `final_adapter`, and `run_receipt.json` appear under `/kaggle/working`.
   Also inspect reward and tool-call logs. A completed run with zero reward,
   zero gradient, and no tool calls proves execution only—not RL learning.
4. Set `CASES_PATH` to the attached real JSONL and switch `CONFIG_PATH` to
   `configs/grpo_kaggle_p100_v0_1.yaml`. Run the training cell again.
5. If Kaggle stops the session, rerun the command with `--resume`. The script
   selects the highest numbered checkpoint automatically.
6. Download the output archive and receipt from the notebook Output panel.
   Keep them with the held-out evaluation report; do not commit model weights.

The final evidence is complete only after Base, LoRA/SFT, and GRPO are evaluated
on the same protected case IDs and the resulting report records quality, tool
behavior, latency, seeds, configuration hashes, and data hashes.

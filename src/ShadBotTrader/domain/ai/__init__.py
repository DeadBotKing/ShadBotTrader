"""AI domain: models, versions, artifacts, training runs and predictions.

Framework-independent bounded context (Phase 13). The AI Platform owns
model identity, definition, versioning, artifacts (with integrity
checksums), training/evaluation runs and predictions. Concrete machine
learning frameworks (TensorFlow/PyTorch) live behind adapters in
``ShadBotTrader.infrastructure.ai``.
"""

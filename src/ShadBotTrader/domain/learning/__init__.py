"""Self-Learning domain — Phase 17.

The controlled learning loop::

    ParameterSpace -> Candidates
                          |
                   in-sample search        (choose parameters here)
                          |
                   walk-forward folds      (judge them here)
                          |
                    PromotionGate          (out-of-sample only)
                          |
              promote / reject -> LearningMemory

Boundary: self-learning proposes, simulation judges, only the gate
approves — and a promotion is a recommendation, never an automatic
change to live trading.
"""

from ShadBotTrader.domain.learning.candidate import (
    Candidate,
    EvaluationRecord,
    best_candidate,
)
from ShadBotTrader.domain.learning.experiment import (
    DataWindow,
    LearningExperiment,
    WalkForwardPlan,
)
from ShadBotTrader.domain.learning.learning_types import (
    CandidateStatus,
    ExperimentStatus,
    ObjectiveDirection,
    RejectionReason,
    SearchStrategy,
    ValidationOutcome,
)
from ShadBotTrader.domain.learning.objective import (
    LearningObjective,
    MaxDrawdownObjective,
    RiskAdjustedObjective,
    SharpeObjective,
    TotalReturnObjective,
)
from ShadBotTrader.domain.learning.parameter_space import (
    CandidateConfiguration,
    ParameterGrid,
    ParameterSpace,
)
from ShadBotTrader.domain.learning.ports import (
    CandidateEvaluator,
    CandidateGenerator,
    ExperimentRepository,
    LearningMemory,
    NullOptimisationReporter,
    OptimisationReporter,
)
from ShadBotTrader.domain.learning.promotion import (
    PromotionGate,
    PromotionPolicy,
    PromotionVerdict,
)

__all__ = [
    "Candidate",
    "CandidateConfiguration",
    "CandidateEvaluator",
    "CandidateGenerator",
    "CandidateStatus",
    "DataWindow",
    "EvaluationRecord",
    "ExperimentRepository",
    "ExperimentStatus",
    "LearningExperiment",
    "LearningMemory",
    "LearningObjective",
    "MaxDrawdownObjective",
    "NullOptimisationReporter",
    "ObjectiveDirection",
    "OptimisationReporter",
    "ParameterGrid",
    "ParameterSpace",
    "PromotionGate",
    "PromotionPolicy",
    "PromotionVerdict",
    "RejectionReason",
    "RiskAdjustedObjective",
    "SearchStrategy",
    "SharpeObjective",
    "TotalReturnObjective",
    "ValidationOutcome",
    "WalkForwardPlan",
    "best_candidate",
]

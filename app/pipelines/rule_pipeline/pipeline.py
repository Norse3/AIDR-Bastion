import re
from pathlib import Path

from app.core.enums import PipelineNames
from app.core.exceptions import ValidationException
from app.models.pipeline import PipelineResult, TriggeredRuleData
from app.modules.logger import bastion_logger
from app.pipelines.base import BaseRulesPipeline


class RulePipeline(BaseRulesPipeline):
    """
    Regular expression-based pipeline for pattern matching in prompts.

    This pipeline uses regular expressions to detect specific patterns in text
    prompts. It loads rules from YAML files and applies regex patterns to
    identify potentially malicious or sensitive content. The pipeline supports
    case-insensitive matching and dot-all mode for comprehensive pattern detection.

    Attributes:
        _identifier (PipelineNames): Pipeline identifier (regex)
        _rules (list): List of loaded regex rules for analysis
    """

    _identifier = PipelineNames.rule
    description = "Regular expression-based pipeline for pattern matching in prompts."
    _rules_dir_path = str(Path(__file__).parent / "rules")

    def _validate_rule_dict(self, rule_dict: dict, file_path: str) -> None:
        """
        Validates regex rule dictionary and compiles patterns.

        Extends base validation to specifically validate regex patterns by
        attempting to compile them. Raises ValidationException for invalid patterns.

        Args:
            rule_dict (dict): Rule dictionary containing regex patterns
            file_path (str): Path to the rule file for error context

        Raises:
            ValidationException: If regex pattern compilation fails
        """
        super()._validate_rule_dict(rule_dict, file_path)
        try:
            for pattern in rule_dict["detection"]["pattern"]:
                re.compile(pattern, re.IGNORECASE | re.DOTALL)
        except re.error:
            bastion_logger.warning(f"Invalid regex pattern, rule_id={rule_dict['uuid']}")
            raise ValidationException()

    async def run(self, prompt: str, **kwargs) -> PipelineResult:
        """
        Analyzes prompt using regex patterns from loaded rules.

        Applies all loaded regex patterns to the input prompt and creates
        triggered rules for any matches found. Uses case-insensitive and
        dot-all matching for comprehensive pattern detection.

        Args:
            prompt (str): Text prompt to analyze for patterns
            **kwargs: Additional keyword arguments (unused)

        Returns:
            PipelineResult: Analysis result with triggered rules and status
        """
        triggered_rules = []
        bastion_logger.info(f"Analyzing for {len(self._rules)} rules")
        for rule in self._rules:
            if re.search(rule.body, prompt):
                triggered_rules.append(
                    TriggeredRuleData(
                        id=rule.id, name=rule.name, details=rule.details, body=rule.body, action=rule.action
                    )
                )
        bastion_logger.info(f"Found {len(triggered_rules)} triggered rules")
        status = self._pipeline_status(triggered_rules)
        bastion_logger.info(f"Analyzing for {len(self._rules)} rules, status: {status}")
        return PipelineResult(name=str(self), triggered_rules=triggered_rules, status=status)

import os
import re
from abc import ABC, abstractmethod

from app.core.dataclasses import Rule
from app.core.enums import ActionStatus, RuleAction
from app.core.exceptions import ValidationException
from app.core.yml_parser import YmlFileParser
from app.models.pipeline import PipelineResult, TriggeredRuleData
from app.modules.logger import bastion_logger


class BasePipeline(ABC):
    """
    Abstract base class for all pipeline implementations.

    This class defines the common interface and functionality that all
    pipelines must implement. It provides basic status determination
    logic and string representation methods.

    Attributes:
        name (str): Pipeline name identifier
        enabled (bool): Whether the pipeline is currently enabled
    """

    name: str
    enabled: bool = False

    def __str__(self) -> str:
        """
        String representation of the pipeline.

        Returns:
            str: Class name of the pipeline
        """
        class_name = self.__class__.__name__
        spaced_name = re.sub(r"(?<!^)(?=[A-Z])", " ", class_name)
        return spaced_name

    def __repr__(self) -> str:
        """
        String representation of the pipeline.

        Returns:
            str: Class name of the pipeline
        """
        return self.__str__()

    @abstractmethod
    async def run(self, prompt: str, **kwargs) -> PipelineResult:
        """
        Abstract method to analyze a prompt for issues.

        This method must be implemented by all concrete pipeline classes.
        It should analyze the provided prompt and return analysis results.

        Args:
            prompt (str): Text prompt to analyze
            **kwargs: Additional keyword arguments

        Returns:
            PipelineResult: Analysis results with triggered rules and status

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError

    def _pipeline_status(self, triggered_rules: list[TriggeredRuleData]) -> ActionStatus:
        """
        Determines overall analysis status based on triggered rules.

        Evaluates the list of triggered rules and returns the highest
        priority action status (BLOCK > NOTIFY > ALLOW).

        Args:
            triggered_rules (list[TriggeredRuleData]): List of triggered rules

        Returns:
            ActionStatus: Overall analysis status based on rule actions
        """
        if any(rule.action == RuleAction.BLOCK for rule in triggered_rules):
            return ActionStatus.BLOCK
        if any(rule.action == RuleAction.NOTIFY for rule in triggered_rules):
            return ActionStatus.NOTIFY
        return ActionStatus.ALLOW


class BaseRulesPipeline(BasePipeline):
    """
    Base class for pipelines that use rule-based detection from YAML files.

    This class provides functionality to load and manage rules from YAML files
    in a specified directory. It handles rule validation, parsing, and storage
    for pipelines that rely on pattern-based detection.

    Attributes:
        _rules (list[Rule]): List of loaded rules
        _rules_dir_path (str | None): Path to directory containing rule files
        _allowed_file_formats (tuple[str]): Supported file formats for rules
    """

    _rules: list[Rule]
    _rules_dir_path: str | None = None
    _allowed_file_formats: tuple[str] = ("yml", "yaml")

    def __init__(self) -> None:
        """
        Initializes the rules pipeline and loads rules from files.

        Loads all rules from the specified directory and enables the pipeline
        if any rules were successfully loaded.
        """
        self._rules = []
        self._load_rules()
        if len(self._rules) > 0:
            self.enabled = True
            bastion_logger.info(f"[{self}] loaded successfully. Total rules: {len(self._rules)}")
        else:
            bastion_logger.warning(f"[{self}] failed to load rules. Total rules: {len(self._rules)}")

    def _load_rules(self) -> None:
        """
        Loads rules from all YAML files in the rules directory.

        Walks through the rules directory and loads rules from all
        supported file formats. Logs the number of loaded rules.
        """
        if not self._rules_dir_path:
            return

        for root, _, files in os.walk(self._rules_dir_path):
            for file in files:
                if file.endswith(self._allowed_file_formats):
                    try:
                        self._load_rules_from_yaml_file(os.path.join(root, file))
                    except Exception:
                        bastion_logger.exception(f"[{self}] Error loading rules from file: {file}")

    def _load_rules_from_yaml_file(self, file_path: str) -> None:
        """
        Loads rules from a single YAML file.

        Parses the YAML file, validates each rule, and adds valid rules
        to the pipeline's rule collection. Skips invalid rules with warnings.

        Args:
            file_path (str): Path to the YAML file to load rules from
        """
        try:
            rule_dicts_gen = YmlFileParser.parse(file_path)
            if not rule_dicts_gen:
                bastion_logger.warning(f"Invalid rule, file_path={file_path}")
                return
            for rule_dict in rule_dicts_gen:
                try:
                    self._validate_rule_dict(rule_dict, file_path)
                except ValidationException:
                    continue
                else:
                    response = rule_dict.get("response")
                    response = RuleAction(response) if response in ("block", "notify") else RuleAction.NOTIFY
                    for pattern in rule_dict["detection"]["pattern"]:
                        self._rules.append(
                            Rule(
                                id=rule_dict["uuid"],
                                name=rule_dict["name"],
                                details=rule_dict["details"],
                                language=rule_dict["detection"]["language"],
                                body=pattern,
                                action=response,
                            )
                        )
        except Exception:
            bastion_logger.exception(f"[{self}] Error loading rules from file: {file_path}")

    def _validate_rule_dict(self, rule_dict: dict, file_path: str) -> None:
        """
        Validates a rule dictionary for required fields.

        Checks that all mandatory fields are present in the rule dictionary
        and raises ValidationException if any are missing.

        Args:
            rule_dict (dict): Rule dictionary to validate
            file_path (str): Path to the rule file for error context

        Raises:
            ValidationException: If required fields are missing
        """
        required_fields = ["uuid", "name", "details", "detection"]
        missing_fields = [field for field in required_fields if field not in rule_dict]
        if missing_fields:
            bastion_logger.warning(
                f"Invalid rule, not all mandatory fields are present, file_path={file_path}, missing_fields={missing_fields}"
            )
            raise ValidationException()
        detection_fields = ["language", "pattern"]
        missing_detection_fields = [field for field in detection_fields if field not in rule_dict["detection"]]
        if missing_detection_fields:
            bastion_logger.warning(
                f"Invalid rule, not all mandatory detection fields are present, file_path={file_path}, missing_detection_fields={missing_detection_fields}"
            )
            raise ValidationException()

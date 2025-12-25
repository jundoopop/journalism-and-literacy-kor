"""
Prompt management system for experimentation and A/B testing.

Allows externalized prompts with versioning, A/B testing, and
performance tracking.
"""

import os
import yaml
import random
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from observability import get_logger

logger = get_logger(__name__)


class PromptTemplate:
    """
    A single prompt template with metadata.

    Attributes:
        name: Template name
        version: Template version (e.g., "v1", "v2")
        template: Prompt template string
        variables: Expected variables for template
        description: Template description
        metadata: Additional metadata
    """

    def __init__(
        self,
        name: str,
        version: str,
        template: str,
        variables: Optional[List[str]] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.version = version
        self.template = template
        self.variables = variables or []
        self.description = description
        self.metadata = metadata or {}

    def render(self, **kwargs) -> str:
        """
        Render template with provided variables.

        Args:
            **kwargs: Variable values

        Returns:
            Rendered prompt string

        Example:
            template = PromptTemplate(
                name="article_analysis",
                version="v1",
                template="Analyze this article: {article_text}",
                variables=["article_text"]
            )

            prompt = template.render(article_text="News article...")
        """
        try:
            # Validate required variables
            missing = [var for var in self.variables if var not in kwargs]
            if missing:
                logger.warning(f"Missing template variables: {missing}")

            return self.template.format(**kwargs)

        except KeyError as e:
            logger.error(f"Template variable not provided: {e}")
            raise ValueError(f"Missing required variable: {e}")

    def __repr__(self):
        return f"<PromptTemplate(name='{self.name}', version='{self.version}')>"


class PromptExperiment:
    """
    A/B test experiment for prompts.

    Attributes:
        name: Experiment name
        description: Experiment description
        active: Whether experiment is active
        traffic_percentage: Percentage of traffic (0-100)
        variants: List of prompt variants
        control_variant: Control variant name
    """

    def __init__(
        self,
        name: str,
        variants: List[Dict[str, Any]],
        active: bool = True,
        traffic_percentage: int = 100,
        control_variant: Optional[str] = None,
        description: Optional[str] = None
    ):
        self.name = name
        self.variants = variants
        self.active = active
        self.traffic_percentage = traffic_percentage
        self.control_variant = control_variant
        self.description = description

    def select_variant(self) -> Optional[str]:
        """
        Select a variant based on traffic percentage and weights.

        Returns:
            Selected variant name or None if experiment not active

        Example:
            experiment = PromptExperiment(
                name="enhanced_prompt",
                variants=[
                    {"name": "control", "weight": 50},
                    {"name": "treatment", "weight": 50}
                ],
                traffic_percentage=50
            )

            variant = experiment.select_variant()
            # Returns "control" or "treatment" 50% of the time
        """
        if not self.active:
            return None

        # Check if this request should be in experiment
        if random.randint(1, 100) > self.traffic_percentage:
            return self.control_variant

        # Select variant based on weights
        total_weight = sum(v.get('weight', 1) for v in self.variants)
        rand_val = random.uniform(0, total_weight)

        current_weight = 0
        for variant in self.variants:
            current_weight += variant.get('weight', 1)
            if rand_val <= current_weight:
                return variant.get('name')

        # Fallback to first variant
        return self.variants[0].get('name') if self.variants else None

    def __repr__(self):
        return f"<PromptExperiment(name='{self.name}', active={self.active})>"


class PromptManager:
    """
    Manages prompt templates and experiments.

    Loads prompts from files and YAML configuration, handles
    template selection based on experiments.

    Example:
        manager = PromptManager()

        # Get prompt for article analysis
        prompt = manager.get_prompt(
            'article_analysis',
            article_text="News article content..."
        )

        # Get active experiment variant
        variant = manager.get_experiment_variant('enhanced_prompt_test')
    """

    def __init__(self, prompts_dir: Optional[Path] = None, experiments_file: Optional[Path] = None):
        """
        Initialize prompt manager.

        Args:
            prompts_dir: Directory containing prompt template files
            experiments_file: YAML file with experiment configurations
        """
        self.logger = get_logger(__name__)

        # Default paths
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent / 'templates'

        if experiments_file is None:
            experiments_file = Path(__file__).parent / 'experiments.yaml'

        self.prompts_dir = prompts_dir
        self.experiments_file = experiments_file

        # Storage
        self._templates: Dict[str, Dict[str, PromptTemplate]] = {}  # {name: {version: template}}
        self._experiments: Dict[str, PromptExperiment] = {}

        # Load prompts and experiments
        self._load_templates()
        self._load_experiments()

    def _load_templates(self):
        """Load all prompt templates from directory."""
        if not self.prompts_dir.exists():
            self.logger.warning(f"Prompts directory not found: {self.prompts_dir}")
            self.prompts_dir.mkdir(parents=True, exist_ok=True)
            return

        # Load .txt and .md files
        for file_path in self.prompts_dir.glob('*.*'):
            if file_path.suffix not in ['.txt', '.md']:
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()

                # Parse filename: {name}_{version}.txt
                name_parts = file_path.stem.split('_')

                if len(name_parts) < 2:
                    name = file_path.stem
                    version = 'v1'
                else:
                    version = name_parts[-1]
                    name = '_'.join(name_parts[:-1])

                # Create template
                template = PromptTemplate(
                    name=name,
                    version=version,
                    template=template_content,
                    variables=self._extract_variables(template_content)
                )

                # Store template
                if name not in self._templates:
                    self._templates[name] = {}

                self._templates[name][version] = template

                self.logger.info(f"Loaded template: {name} ({version})")

            except Exception as e:
                self.logger.error(f"Failed to load template {file_path}", exc=e)

    def _load_experiments(self):
        """Load experiment configurations from YAML."""
        if not self.experiments_file.exists():
            self.logger.info(f"Experiments file not found: {self.experiments_file}")
            # Create default experiments file
            self._create_default_experiments_file()
            return

        try:
            with open(self.experiments_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            if not config or 'experiments' not in config:
                self.logger.warning("No experiments found in config")
                return

            for exp_config in config['experiments']:
                experiment = PromptExperiment(
                    name=exp_config['name'],
                    variants=exp_config['variants'],
                    active=exp_config.get('active', True),
                    traffic_percentage=exp_config.get('traffic_percentage', 100),
                    control_variant=exp_config.get('control_variant'),
                    description=exp_config.get('description')
                )

                self._experiments[experiment.name] = experiment

                self.logger.info(f"Loaded experiment: {experiment.name} (active={experiment.active})")

        except Exception as e:
            self.logger.error("Failed to load experiments", exc=e)

    def _create_default_experiments_file(self):
        """Create default experiments configuration."""
        default_config = {
            'experiments': [
                {
                    'name': 'article_analysis_prompt',
                    'description': 'Test different prompts for article analysis',
                    'active': False,
                    'traffic_percentage': 50,
                    'control_variant': 'v1',
                    'variants': [
                        {'name': 'v1', 'weight': 50},
                        {'name': 'v2', 'weight': 50}
                    ]
                }
            ]
        }

        try:
            self.experiments_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.experiments_file, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False)

            self.logger.info(f"Created default experiments file: {self.experiments_file}")

        except Exception as e:
            self.logger.error("Failed to create default experiments file", exc=e)

    def _extract_variables(self, template: str) -> List[str]:
        """
        Extract variable names from template string.

        Args:
            template: Template string

        Returns:
            List of variable names
        """
        import re
        # Match {variable_name} patterns
        pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
        matches = re.findall(pattern, template)
        return list(set(matches))

    def get_prompt(
        self,
        name: str,
        version: Optional[str] = None,
        experiment: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Get rendered prompt.

        Args:
            name: Prompt template name
            version: Specific version (optional)
            experiment: Experiment name to use (optional)
            **kwargs: Template variables

        Returns:
            Rendered prompt string

        Example:
            # Get latest version
            prompt = manager.get_prompt('article_analysis', article_text="...")

            # Get specific version
            prompt = manager.get_prompt('article_analysis', version='v2', article_text="...")

            # Use experiment to select version
            prompt = manager.get_prompt(
                'article_analysis',
                experiment='enhanced_prompt_test',
                article_text="..."
            )
        """
        # Check experiment first
        if experiment and experiment in self._experiments:
            exp = self._experiments[experiment]
            selected_variant = exp.select_variant()

            if selected_variant:
                version = selected_variant
                self.logger.info(
                    f"Selected variant '{selected_variant}' from experiment '{experiment}'"
                )

        # Get template
        if name not in self._templates:
            raise ValueError(f"Template '{name}' not found")

        versions = self._templates[name]

        # Select version
        if version and version in versions:
            template = versions[version]
        else:
            # Use latest version (highest version key)
            template = versions[max(versions.keys())]

        # Render template
        return template.render(**kwargs)

    def get_experiment_variant(self, experiment_name: str) -> Optional[str]:
        """
        Get selected variant for an experiment.

        Args:
            experiment_name: Experiment name

        Returns:
            Selected variant name or None
        """
        if experiment_name not in self._experiments:
            return None

        return self._experiments[experiment_name].select_variant()

    def reload(self):
        """Reload templates and experiments from disk."""
        self.logger.info("Reloading prompts and experiments")
        self._templates.clear()
        self._experiments.clear()
        self._load_templates()
        self._load_experiments()

    def list_templates(self) -> List[Dict[str, Any]]:
        """
        List all available templates.

        Returns:
            List of template info dictionaries
        """
        templates = []

        for name, versions in self._templates.items():
            for version, template in versions.items():
                templates.append({
                    'name': name,
                    'version': version,
                    'variables': template.variables,
                    'description': template.description
                })

        return templates

    def list_experiments(self) -> List[Dict[str, Any]]:
        """
        List all experiments.

        Returns:
            List of experiment info dictionaries
        """
        experiments = []

        for exp in self._experiments.values():
            experiments.append({
                'name': exp.name,
                'description': exp.description,
                'active': exp.active,
                'traffic_percentage': exp.traffic_percentage,
                'variants': [v['name'] for v in exp.variants]
            })

        return experiments

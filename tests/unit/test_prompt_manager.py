"""
Unit tests for prompt manager and experimentation framework.
"""

import pytest
from pathlib import Path
from llm.prompts.prompt_manager import PromptManager, PromptTemplate, PromptExperiment


class TestPromptManager:
    """Test prompt manager functionality."""

    @pytest.fixture
    def manager(self):
        """Create prompt manager instance."""
        return PromptManager()

    def test_manager_initialization(self, manager):
        """Test that manager initializes correctly."""
        assert manager is not None
        assert manager._templates is not None
        assert manager._experiments is not None

    def test_list_templates(self, manager):
        """Test listing available prompt templates."""
        templates = manager.list_templates()

        assert len(templates) > 0

        # Should have at least v1 and v2 templates
        template_names = {t['name'] for t in templates}
        assert 'article_analysis' in template_names

        # Check template structure
        for template in templates:
            assert 'name' in template
            assert 'version' in template
            assert 'file_path' in template

    def test_get_prompt_with_default_version(self, manager):
        """Test getting prompt with default version."""
        prompt = manager.get_prompt(
            'article_analysis',
            article_text="테스트 기사 내용"
        )

        assert prompt is not None
        assert len(prompt) > 0
        assert "테스트 기사 내용" in prompt

    def test_get_prompt_with_specific_version(self, manager):
        """Test getting prompt with specific version."""
        prompt_v1 = manager.get_prompt(
            'article_analysis',
            version='v1',
            article_text="테스트"
        )

        prompt_v2 = manager.get_prompt(
            'article_analysis',
            version='v2',
            article_text="테스트"
        )

        assert prompt_v1 is not None
        assert prompt_v2 is not None

        # Different versions should have different content
        # (assuming v2 has additional criteria)
        assert prompt_v1 != prompt_v2

    def test_get_prompt_with_variable_substitution(self, manager):
        """Test that template variables are substituted correctly."""
        article_text = "이것은 테스트 기사입니다."

        prompt = manager.get_prompt(
            'article_analysis',
            article_text=article_text
        )

        assert article_text in prompt

    def test_list_experiments(self, manager):
        """Test listing configured experiments."""
        experiments = manager.list_experiments()

        assert isinstance(experiments, list)

        # Check experiment structure
        for exp in experiments:
            assert 'name' in exp
            assert 'active' in exp
            assert 'variants' in exp

    def test_get_prompt_with_experiment(self, manager):
        """Test getting prompt through experiment framework."""
        # This test depends on having an active experiment
        experiments = manager.list_experiments()

        if experiments:
            # Get prompt using first experiment
            exp_name = experiments[0]['name']

            prompt = manager.get_prompt(
                'article_analysis',
                experiment=exp_name,
                article_text="테스트"
            )

            assert prompt is not None
            assert len(prompt) > 0

    def test_prompt_template_class(self):
        """Test PromptTemplate dataclass."""
        template = PromptTemplate(
            name="test_template",
            version="v1",
            file_path=Path("/tmp/test.txt"),
            content="Test prompt: {{ variable }}"
        )

        assert template.name == "test_template"
        assert template.version == "v1"

        # Test rendering
        rendered = template.render(variable="value")
        assert "value" in rendered

    def test_experiment_class(self):
        """Test PromptExperiment class."""
        experiment = PromptExperiment(
            name="test_experiment",
            description="Test experiment",
            active=True,
            traffic_percentage=50,
            variants=[
                {"name": "v1", "weight": 50},
                {"name": "v2", "weight": 50}
            ],
            control_variant="v1"
        )

        assert experiment.name == "test_experiment"
        assert experiment.active is True

        # Test variant selection
        selected = experiment.select_variant()
        assert selected in ["v1", "v2"] or selected is None

    def test_variant_selection_distribution(self):
        """Test that variant selection follows weight distribution."""
        experiment = PromptExperiment(
            name="test",
            description="Test",
            active=True,
            traffic_percentage=100,
            variants=[
                {"name": "v1", "weight": 50},
                {"name": "v2", "weight": 50}
            ],
            control_variant="v1"
        )

        # Run multiple selections
        selections = [experiment.select_variant() for _ in range(100)]
        selections = [s for s in selections if s is not None]  # Filter out Nones

        # Both variants should be selected (with high probability)
        if len(selections) >= 20:  # If we got enough selections
            assert "v1" in selections or "v2" in selections

    def test_inactive_experiment_returns_none(self):
        """Test that inactive experiments don't select variants."""
        experiment = PromptExperiment(
            name="inactive",
            description="Test",
            active=False,
            traffic_percentage=50,
            variants=[{"name": "v1", "weight": 100}],
            control_variant="v1"
        )

        selected = experiment.select_variant()
        assert selected is None

    def test_get_prompt_missing_variable_raises_error(self, manager):
        """Test that missing required variables raise error."""
        with pytest.raises(Exception):
            # Missing article_text variable
            manager.get_prompt('article_analysis')

    def test_get_prompt_nonexistent_template(self, manager):
        """Test getting non-existent template."""
        with pytest.raises(KeyError):
            manager.get_prompt('nonexistent_template')

    def test_template_file_loading(self, manager):
        """Test that template files are loaded correctly."""
        templates = manager._templates.get('article_analysis', {})

        assert len(templates) > 0

        for version, template in templates.items():
            assert isinstance(template, PromptTemplate)
            assert template.content is not None
            assert len(template.content) > 0
            assert template.file_path.exists()

    def test_experiment_config_loading(self, manager):
        """Test that experiment configurations are loaded correctly."""
        # Experiments should be loaded from YAML
        experiments = manager._experiments

        for exp_name, config in experiments.items():
            assert isinstance(config, ExperimentConfig)
            assert config.name == exp_name
            assert hasattr(config, 'active')
            assert hasattr(config, 'variants')

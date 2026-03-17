import unittest
from pathlib import Path
from src.package_schema import PackageProfile, WorkflowBundle, DeploymentProfile, ConversionArtifact
from src.package_profiles import load_package_profiles, get_package_profile
from src.workflow_bundles import load_workflow_bundles, get_workflow_bundle
from src.deployment_profiles import load_deployment_profiles, get_deployment_profile
from src.adoption_readiness import summarize_adoption_readiness

class TestPhase22(unittest.TestCase):
    def test_package_profiles_loading(self):
        # Assumes the data/package_profiles.yaml exists
        path = Path("src/resources/data/package_profiles.yaml")
        profiles = load_package_profiles(path)
        self.assertGreater(len(profiles), 0)
        p = get_package_profile(profiles, "research_team_pilot")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "research_team_pilot")

    def test_workflow_bundles_loading(self):
        path = Path("src/resources/data/workflow_bundles.yaml")
        bundles = load_workflow_bundles(path)
        self.assertGreater(len(bundles), 0)
        b = get_workflow_bundle(bundles, "weekly_review")
        self.assertIsNotNone(b)
        self.assertEqual(b.name, "weekly_review")

    def test_deployment_profiles_loading(self):
        path = Path("src/resources/data/deployment_profiles.yaml")
        profiles = load_deployment_profiles(path)
        self.assertGreater(len(profiles), 0)
        p = get_deployment_profile(profiles, "small_compbio_team")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "small_compbio_team")

    def test_adoption_readiness_summary(self):
        artifacts = [
            ConversionArtifact("p1", ["w1"], ["a1"], ["f1"], ["n1"], 0.8),
            ConversionArtifact("p2", ["w1", "w2"], ["a1", "a2"], ["f1"], ["n2"], 0.9)
        ]
        summary = summarize_adoption_readiness(artifacts)
        self.assertEqual(summary["total_pilots"], 2)
        self.assertAlmostEqual(summary["average_readiness_score"], 0.85)
        self.assertIn("f1", summary["common_friction_points"])
        self.assertIn("a1", summary["most_useful_artifacts"])

if __name__ == "__main__":
    unittest.main()

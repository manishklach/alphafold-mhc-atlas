from src.demo_loader import list_demo_projects, load_demo_readme, resolve_demo_project


def test_demo_loader_lists_and_resolves_projects() -> None:
    demos = list_demo_projects()
    assert "small_project" in demos
    path = resolve_demo_project("small_project")
    assert path.exists()
    assert "lightweight" in load_demo_readme("small_project").lower()

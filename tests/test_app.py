def test_app_entrypoint_imports():
    import app

    assert callable(app.render_dashboard)
Business outputs are generated at runtime.

To generate:
1. Import a margin file using cli.py
2. HTML Dashboard: dashboard_generator.generate_dashboard(repo, path)
3. Power BI exports: powerbi_connector.refresh_all(repo_dir, output_dir)
4. Forecast override: forecast_integration.generate_forecast_override(repo, path)
5. Alert report: alerts.scan_alerts(repo) + alerts.format_alert_text(alerts)
6. Simulation: simulator.simulate_margin_change(article, changes)

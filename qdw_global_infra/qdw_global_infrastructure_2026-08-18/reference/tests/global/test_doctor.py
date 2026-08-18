def test_doctor_checks_foreign_keys_and_global_tables(system):
    d=system.doctor()
    assert d["ok"]
    assert d["global"]["missing_tables"]==[]
    assert d["global"]["foreign_key_violations"]==[]

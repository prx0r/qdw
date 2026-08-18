from qdw.interfaces.federation_api import protocol

def test_only_committed_is_terminal_federation_success():
    x=protocol()
    assert x["terminal_success_states"]==["COMMITTED"]
    assert x["authority"]=={"workgraph":"qdw","final_route":"qdw","verification":"qdw"}

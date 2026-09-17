from app.agent.agent import SYSTEM_PROMPT, build_system_prompt


def test_build_system_prompt_without_usuario_returns_base_prompt():
    assert build_system_prompt(None) == SYSTEM_PROMPT


def test_build_system_prompt_includes_usuario_fields():
    usuario = {
        "ruc": "20100047218",
        "razon_social": "BANCO DE CREDITO DEL PERU",
        "estado": "ACTIVO",
        "condicion": "HABIDO",
        "direccion": "JR. CENTENARIO NRO 156",
        "ubigeo": "150114",
    }

    prompt = build_system_prompt(usuario)

    assert SYSTEM_PROMPT in prompt
    assert "20100047218" in prompt
    assert "BANCO DE CREDITO DEL PERU" in prompt
    assert "150114" in prompt
    assert "JR. CENTENARIO NRO 156" in prompt

def _build_qwenlm(tp=1):
    from llms.QwenLM import QwenLM

    return QwenLM(tp=tp)


def _build_qwenvl(tp=1):
    from llms.QwenVL import QwenVL

    return QwenVL(tp=tp)


def _build_gemini(tp=1):
    from llms.Gemini import Gemini

    return Gemini()


def _build_gemini25flash(tp=1):
    from llms.Gemini import Gemini

    return Gemini(model_type="gemini-2.5-flash")


def _build_gemini25pro(tp=1):
    from llms.Gemini import Gemini

    return Gemini(model_type="gemini-2.5-pro")


def _build_gpt4o(tp=1):
    from llms.OpenAIChat import OpenAIChat

    return OpenAIChat(model_type="gpt-4o")


def _build_gpt41(tp=1):
    from llms.OpenAIChat import OpenAIChat

    return OpenAIChat(model_type="gpt-4.1")


model_zoo = {
    "qwenlm": _build_qwenlm,
    "qwenvl": _build_qwenvl,
    "gemini": _build_gemini,
    "gemini25flash": _build_gemini25flash,
    "gemini25pro": _build_gemini25pro,
    "gpt4o": _build_gpt4o,
    "gpt41": _build_gpt41,
}

def init_model(model_name, num_gpus=1):
    if model_name not in model_zoo:
        supported_models = ", ".join(model_zoo.keys())
        raise ValueError(f"Model {model_name} not found in model_zoo. Supported models: {supported_models}")
    model_builder = model_zoo[model_name]
    return model_builder(tp=num_gpus)

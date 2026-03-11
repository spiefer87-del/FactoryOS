MASTERDATA_REGISTRY = {}


def register_masterdata(name, model, search_fields=None):

    MASTERDATA_REGISTRY[name] = {
        "model": model,
        "search_fields": search_fields or []
    }


def get_masterdata(name):

    return MASTERDATA_REGISTRY.get(name)


def list_masterdata():

    return MASTERDATA_REGISTRY

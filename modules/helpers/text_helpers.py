def format_longtext(data, max_length=30000):
    """ Formate un champ longtext pour l'afficher dans une liste (abrégé + multi-lignes). """
    if isinstance(data, dict):
        text = data.get("text", "")
    else:
        text = str(data)

    text = text.replace("\n", " ").strip()

    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

import sys

sys.path.append("../src")

from src.multiblimp.ud2um import create_all_unimorph_from_ud
from src.multiblimp.languages import get_ud_langs
from src.config.paths import RESOURCES


if __name__ == "__main__":
    resource_dir = RESOURCES
    ud_langs = ["Turkish", "Polish", "Hungarian", "Belarusian", "Russian", "Ukrainian", "Romanian", "Finnish", "Lithuanian", "Slovenian", "Persian"]

    create_all_unimorph_from_ud(
        ud_langs,
        resource_dir=resource_dir,
        load_from_pickle=False,
        dup_form_threshold=3.0,
        dup_feat_threshold=10.0,
    )

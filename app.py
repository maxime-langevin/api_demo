import base64
import streamlit as st
import pandas as pd
import logging
import sys
import time
import matplotlib.pyplot as plt
from matplotlib.colors import to_hex
import numpy as np
import requests
import json
import base64
from PIL import Image
from base64 import b64decode

from utils import logger, result_search
from hprim2response import hprim2response
import re
from io import StringIO


def float_if_possible(x):
    try:
        return float(x)
    except ValueError:
        return x


image = Image.open("images/deepia_logo.png")
left_co, cent_co, last_co = st.columns(3)
with cent_co:
    st.image(
        image,
        caption="L'analyse biologique intelligente.",
        use_column_width=True,
    )

st.markdown("#")
st.markdown("#")
st.header(":file_folder: **Biologia API** Plugin :", divider="blue")
st.markdown("##")
# Emoji link : https://streamlit-emoji-shortcodes-streamlit-app-gwckff.streamlit.app


def remove_non_ascii(text):
    return re.sub(r"[^\x00-\x7F]+", "", text)


hprim_base = ""


def color_background_red_column(col):
    return ["background: red" for _ in col]


def scalar_to_color(value, bound, interval, colormap="Reds"):
    normed_value = np.abs(value - bound) / interval
    normed_value = max(0.05, normed_value)
    color = plt.get_cmap(colormap)(normed_value)
    return to_hex(color)


def highlight(x):
    value = x["Valeur"]
    bin = x["BIN"]
    bsn = x["BSN"]
    if isinstance(bin, float) and isinstance(bsn, float):
        interval = bsn - bin
        if value < bsn and value > bin:
            color = ""
        elif value >= bsn:
            color = f"background-color: {scalar_to_color(value, bsn, interval, colormap='Purples')}"
        elif value <= bin:
            color = f"background-color: {scalar_to_color(value, bin, interval, colormap='Oranges')}"
        else:
            color = ""
    else:
        color = ""
    return [color] * len(x)


# Colors : https://matplotlib.org/stable/gallery/color/colormap_reference.html

css = """
<style>
[data-testid="stFileUploaderDropzone"] div div::before {color:black; content:"Ajouter un fichier."}
[data-testid="stFileUploaderDropzone"] div div span{display:none;}
[data-testid="stFileUploaderDropzone"] div div::after {color:grey; font-size: .8em; content:"Limite de 200MB par fichier - hprim "}
[data-testid="stFileUploaderDropzone"] div div small{display:none;}
</style>
"""

st.markdown(css, unsafe_allow_html=True)

data = {
    "Nom": [],
    "Valeur": [],
    "Unité": [],
    "BIN": [],
    "BSN": [],
}
df = pd.DataFrame.from_dict(data)


uploaded_file = st.file_uploader(
    "Choisir un compte-rendu de biologie médicale (hprim)",
    accept_multiple_files=False,
    type=["hprim"],
)


if uploaded_file is not None:
    hprim_base = ""
    hprim = uploaded_file.getvalue().splitlines()

    data = {
        "Nom": [],
        "Valeur": [],
        "Unité": [],
        "BIN": [],
        "BSN": [],
    }
    df = pd.DataFrame.from_dict(data)

    for hprim_line in hprim:
        hprim_line = hprim_line.decode("utf-8")
        if hprim_line.startswith("RES"):
            hprim_base += f"\n{hprim_line}"
            splitted_line = hprim_line.split("|")

            line = {
                "Nom": splitted_line[1],
                "Valeur": float_if_possible(splitted_line[4]),
                "Unité": splitted_line[5],
                "BIN": float_if_possible(splitted_line[6]),
                "BSN": float_if_possible(splitted_line[7]),
            }
            df.loc[len(df)] = line
    json_response = hprim2response(base64.b64encode(uploaded_file.getvalue()))
    n_anomalies = len(json_response["anomalies"])
    if n_anomalies == 0:
        st.warning(f"Notre logiciel n'a identifié aucune anomalie dans ce bilan biologique.")
    elif n_anomalies == 1:
        st.warning(f"Notre logiciel a identifié {n_anomalies} anomalie dans ce bilan biologique.")
    else:
        st.warning(f"Notre logiciel a identifié {n_anomalies} anomalies dans ce bilan biologique.")

    # codes already used
    used_codes = []

    for anomaly in json_response["anomalies"]:
        with st.container(border=True):
            label = anomaly["label"]
            sources = {}
            for source in anomaly["sources"]:
                source_label = source["label"]
                source_date = source["date"]
                source_name = f"{source_label}, {source_date}"
                sources[source_name] = source["link"]

            conditions = anomaly["linked_measure_codes"]
            conditions_display = []

            for condition in conditions:
                used_codes.append(condition.lower())
                if condition == "ALBCREAU":
                    condition = "albprotu"
                transcript = json_response["measures"]
                for k, v in transcript.items():
                    if v["code_lambda"].lower() == condition.lower():
                        matched_transcript = v

                conditions_display.append(
                    {
                        "name": matched_transcript["human_readable"],
                        "unit": matched_transcript["unit"],
                        "value": matched_transcript["value"],
                    }
                )

            result_string = "Marqueurs biologiques impliquées: "

            for condition in conditions_display:
                name = condition["name"]
                value = condition["value"]
                unit = condition["unit"]
                result_string += f" {name} ({value} {unit}),"
            result_string = result_string[:-1]

            text = f"Anomalie identifiée : **{label}**.  \n {result_string}"

            st.success(text)

            if anomaly["urgent"]:
                st.warning("Urgent", icon="⚠️")
            else:
                st.warning("Pathologique, non urgent", icon="⚠️")

            recos = ""
            for exploration in anomaly["explorations"]:
                name = exploration["ordo_title"]
                exams = [x["label"] for x in exploration["exams"]]
                recos += f"**{name}** : "
                recos += ", ".join(exams)
                recos += "  \n"
            st.info(recos)
            documentations = anomaly["documentations"]
            docs = {}
            for documentation in documentations:
                docs[documentation["title"]] = documentation["body"]
            st.info(
                "Documentation additionnelle sur l'anomalie et les recommandations d'examens complémentaires."
            )
            with st.popover("Documentation", use_container_width=True):
                for k, v in docs.items():
                    st.write(b64decode(v).decode("utf-8"))
            with st.popover("Sources", use_container_width=True):
                for i, (k, v) in enumerate(sources.items()):
                    st.write(f"**Source {i+1}** : {k}.  \nLien : {v}")

    # display other markers not used in the analysis
    codes_to_display = {}
    transcript = json_response["measures"]
    for k, v in transcript.items():
        if not v["normal"] and v["code_lambda"].lower() not in used_codes:

            category = v["category"]
            name = v["human_readable"]
            value = v["value"]
            unit = v["unit"]
            lin = v["bin"]
            lsn = v["bsn"]
            if category in codes_to_display.keys():
                codes_to_display[
                    category.capitalize()
                ] += f', {name} - **{value} {unit or ""}** ({lin or ""} - {lsn or ""} {unit or ""})'
            else:
                codes_to_display[category.capitalize()] = (
                    f' {name} - **{value} {unit or ""}** ({lin or ""} - {lsn or ""} {unit or ""})'
                )

    full_text_other_anomalies = "Autres marqueurs biologiques anormaux :  \n"
    for cat, marqueurs in codes_to_display.items():
        full_text_other_anomalies += f"**{cat}** : {marqueurs}.  \n"
    st.success(full_text_other_anomalies)
    df = df.round(1).set_index(df.columns[0])
    styled_df = df.style.apply(highlight, axis=1).format(precision=1).hide(axis="index")

    st.table(styled_df)

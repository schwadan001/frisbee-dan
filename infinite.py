from bs4 import BeautifulSoup
from datetime import datetime
from functools import reduce
from itertools import chain
from multiprocessing import Pool
import pandas as pd
import re
from urllib.request import urlopen

url = "https://infinitediscs.com"
output_file = "discs.csv"

disc_attrs = {
    "name": {
        "id": "ContentPlaceHolder1_lblDiscName",
        "type": "h1",
        "f": lambda x: x.text.strip()
    },
    "diameter": {
        "id": "ContentPlaceHolder1_lblDiameter",
        "type": "li",
        "f": lambda x: x.text.replace("Diameter:", "").strip()
    },
    "height": {
        "id": "ContentPlaceHolder1_lblHeight",
        "type": "li",
        "f": lambda x: x.text.replace("Height:", "").strip()
    },
    "rim_depth": {
        "id": "ContentPlaceHolder1_lblRimDepth",
        "type": "li",
        "f": lambda x: x.text.replace("Rim Depth:", "").strip()
    },
    "rim_width": {
        "id": "ContentPlaceHolder1_lblRimWidth",
        "type": "li",
        "f": lambda x: x.text.replace("Rim Width:", "").strip()
    },
    "speed": {
        "id": "ContentPlaceHolder1_lblSpeed",
        "type": "li",
        "f": lambda x: float(x.text.replace("Speed:", "").strip())
    },
    "glide": {
        "id": "ContentPlaceHolder1_lblGlide",
        "type": "li",
        "f": lambda x: float(x.text.replace("Glide:", "").strip())
    },
    "turn": {
        "id": "ContentPlaceHolder1_lblTurn",
        "type": "li",
        "f": lambda x: float(x.text.replace("Turn:", "").strip())
    },
    "fade": {
        "id": "ContentPlaceHolder1_lblFade",
        "type": "li",
        "f": lambda x: float(x.text.replace("Fade:", "").strip())
    },
    "stability": {
        "id": "ContentPlaceHolder1_lblStability",
        "type": "li",
        "f": lambda x: x.text.replace("Stability:", "").strip()
    },
    "bead": {
        "id": "ContentPlaceHolder1_lblBeadless",
        "type": "li",
        "f": lambda x: x.text.strip()
    }
}


def flatten_li(arr):
    flat_arr = []
    for li in arr:
        if li.find("li") == None:
            flat_arr.append(li.find("a"))
        else:
            [flat_arr.append(sub_li.find("a")) for sub_li in li.findAll("li")]
    return flat_arr


def get_manufacturer_discs(mfg):
    print("Researching manufacturer: {}".format(mfg["text"]))
    html = urlopen(url + mfg["href"]).read()
    soup = BeautifulSoup(html, features="html.parser")

    mfg_discs = []
    for disc_type in ["DD", "CD", "MR", "PT"]:
        disc_refs = get_disc_refs(
            soup.find("div", {"id": "ContentPlaceHolder1_pnl" + disc_type})
        )
        for disc_ref in disc_refs:
            mfg_discs.append(
                {"manufacturer": mfg["text"], "link": url + disc_ref}
            )
    return mfg_discs


def get_disc_refs(category):
    try:
        return [
            itm.findAll("button")[-1]["onclick"].split("=")[1].strip("'")
            for itm in category.findAll("div", {"class": "thumbnail"})
        ]
    except Exception:
        return []


def get_disc_info(disc):
    html = urlopen(disc["link"]).read()
    soup = BeautifulSoup(html, features="html.parser")

    for key in disc_attrs:
        attr = disc_attrs[key]
        try:
            disc[key] = attr["f"](
                soup.find(attr["type"], {"id": attr["id"]}))
        except Exception:
            disc[key] = None

    print("{} - {}".format(disc["manufacturer"], disc["name"]))
    return disc


if __name__ == "__main__":
    start_time = datetime.now()
    
    html = urlopen(url).read()
    soup = BeautifulSoup(html, features="html.parser")

    pool = Pool(processes=8)

    menu = soup.find("div", {"id": "main-menu"})
    menu_items = [li for li in flatten_li(menu.findAll("li")) if li != None]
    mfgs = [{"text": itm.text, "href": itm["href"]}
            for itm in menu_items if "/category/" in itm["href"]]
    mfgs_dedupe = [dict(t) for t in {tuple(d.items()) for d in mfgs}]

    mfg_discs_grouped = pool.map(get_manufacturer_discs, mfgs_dedupe)
    mfg_discs = [d for d in reduce(chain, mfg_discs_grouped)]

    print("\nResearching discs...")
    discs = pool.map(get_disc_info, mfg_discs)

    # write disc info to csv file
    df = pd.DataFrame(discs).sort_values(
        by=["manufacturer", "speed", "turn", "fade", "name"]
    )
    df = df[[
        "manufacturer",
        "name",
        "speed",
        "glide",
        "turn",
        "fade",
        "diameter",
        "height",
        "rim_depth",
        "rim_width",
        "bead",
        "stability",
        "link"
    ]]

    df.to_csv(output_file, index=False)

    print("\nData load complete. Took {} minute(s)".format(
        int((datetime.now() - start_time).seconds / 60)
    ))
    input()

import re
from bs4 import BeautifulSoup

class GestisParser:
    @staticmethod
    def parse_article(json_data):
        """
        Parses GESTIS JSON article data based on chapter numbers.
        Replicates the logic from the original Rust implementation.
        """
        if not json_data:
            return None
            
        chapters = json_data.get("hauptkapitel", [])
        mapping = {}

        # Map chapter numbers to their HTML content
        for ch in chapters:
            ch_num = ch.get("drnr")
            for sub in ch.get("unterkapitel", []):
                sub_num = sub.get("drnr")
                text = sub.get("text", "")
                mapping[f"{ch_num}_{sub_num}"] = text

        data = {
            "name": json_data.get("name", ""),
            "cas": "",
            "formula": "",
            "molar_mass": "",
            "melting_point": "",
            "boiling_point": "",
            "ghs_symbols": [],
            "signal_word": "",
            "h_phrases": [],
            "p_phrases": [],
            "wgk": "",
            "mak_ld50": ""
        }

        # 1. CAS (0100_0100)
        cas_html = mapping.get("0100_0100")
        if cas_html:
            soup = BeautifulSoup(cas_html, "html.parser")
            cas_tag = soup.find("casnr")
            if cas_tag:
                data["cas"] = cas_tag.get_text(strip=True)

        # 2. Formula / Molar Mass (0400_0400)
        mass_html = mapping.get("0400_0400")
        if mass_html:
            soup = BeautifulSoup(mass_html, "html.parser")
            formula_tag = soup.find("summenformel")
            if formula_tag:
                data["formula"] = formula_tag.get_text(strip=True)
            
            mol_text = soup.find(string=re.compile(r"Molmasse:"))
            if mol_text:
                td = mol_text.find_parent("td")
                if td:
                    next_td = td.find_next_sibling("td")
                    if next_td:
                        data["molar_mass"] = next_td.get_text(strip=True)

        # 3. Melting / Boiling Point (0600_0602, 0600_0603)
        for key, field in [("0600_0602", "melting_point"), ("0600_0603", "boiling_point")]:
            html = mapping.get(key)
            if html:
                soup = BeautifulSoup(html, "html.parser")
                table = soup.find("table", class_="feldmitlabel")
                if table:
                    tds = table.find_all("td")
                    if len(tds) >= 2:
                        data[field] = tds[1].get_text(strip=True)

        # 4. WGK (1100_1106)
        wgk_html = mapping.get("1100_1106")
        if wgk_html:
            soup = BeautifulSoup(wgk_html, "html.parser")
            # Usually looks like "WGK 1" or similar
            text = soup.get_text()
            match = re.search(r"WGK\s+\d+", text)
            if match:
                data["wgk"] = match.group(0)

        # 5. GHS / H / P (1100_1303)
        ghs_html = mapping.get("1100_1303")
        if ghs_html:
            soup = BeautifulSoup(ghs_html, "html.parser")
            
            # Signal word
            sig_table = soup.find("table")
            if sig_table:
                sig_tds = sig_table.find_all("td")
                if len(sig_tds) >= 2:
                    data["signal_word"] = sig_tds[1].get_text(strip=True).replace('"', '')

            # Symbols
            for img in soup.find_all("img"):
                alt = img.get("alt")
                if alt:
                    data["ghs_symbols"].append(alt)
            data["ghs_symbols"] = sorted(list(set(data["ghs_symbols"])))

            # H-Phrases
            h_text = soup.find(string=re.compile(r"H-Sätze:"))
            if h_text:
                td = h_text.find_parent("td")
                if td:
                    next_td = td.find_next_sibling("td")
                    if next_td:
                        # Extract H-codes and their descriptions
                        text_content = next_td.get_text("\n")
                        # Split by line and look for "Hxxx: text"
                        lines = text_content.split("\n")
                        for line in lines:
                            if ":" in line:
                                code, desc = line.split(":", 1)
                                if code.strip().startswith("H"):
                                    data["h_phrases"].append({"id": code.strip(), "text": desc.strip()})

            # P-Phrases
            p_text = soup.find(string=re.compile(r"P-Sätze:"))
            if p_text:
                td = p_text.find_parent("td")
                if td:
                    next_td = td.find_next_sibling("td")
                    if next_td:
                        text_content = next_td.get_text("\n")
                        lines = text_content.split("\n")
                        for line in lines:
                            if ":" in line:
                                code, desc = line.split(":", 1)
                                if code.strip().startswith("P"):
                                    data["p_phrases"].append({"id": code.strip(), "text": desc.strip()})

        # 6. LD50 (0500_0501)
        ld_html = mapping.get("0500_0501")
        if ld_html:
            soup = BeautifulSoup(ld_html, "html.parser")
            ld_text = soup.find(string=re.compile(r"LD50 oral Ratte"))
            if ld_text:
                td = ld_text.find_parent("td")
                if td:
                    next_td = td.find_next_sibling("td")
                    if next_td:
                        data["mak_ld50"] = next_td.get_text(strip=True)

        return data

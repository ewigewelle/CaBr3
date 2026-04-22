import re

class GestisParser:
    @staticmethod
    def parse_article(json_data):
        """
        Parses GESTIS JSON article data based on chapter numbers.
        Highly robust version using flexible regex patterns.
        """
        from bs4 import BeautifulSoup
        if not json_data:
            return None
            
        chapters = json_data.get("hauptkapitel", [])
        mapping = {}

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
            "mak": "",
            "ld50": "",
            "gefahren": [],
            "schutzmassnahmen": [],
            "verhalten": [],
            "entsorgung": []
        }

        # 1. CAS (0100_0100)
        # ... (rest stays the same)
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
            
            # Robust extraction of Molar Mass
            text = soup.get_text(separator=" ")
            mol_match = re.search(r"(?:Molmasse|Molar\s*mass)\s*[:]?\s*([\d,\.]+)\s*g/mol", text, re.IGNORECASE)
            if mol_match:
                data["molar_mass"] = mol_match.group(1).replace(",", ".")
            else:
                # Try finding any number followed by g/mol if specifically in chapter 0400_0400
                mol_match = re.search(r"([\d,\.]+)\s*g/mol", text)
                if mol_match:
                    data["molar_mass"] = mol_match.group(1).replace(",", ".")
                else:
                    # Fallback if text search fails, try label search
                    mol_label = soup.find(string=re.compile(r"Molmasse", re.I))
                    if mol_label:
                        td = mol_label.find_parent("td")
                        if td:
                            next_td = td.find_next_sibling("td")
                            if next_td:
                                data["molar_mass"] = re.sub(r"[^\d,\.]", "", next_td.get_text(strip=True)).replace(",", ".")

        # 3. Melting / Boiling Point (0600_0602, 0600_0603)
        for key, field in [("0600_0602", "melting_point"), ("0600_0603", "boiling_point")]:
            html = mapping.get(key)
            if html:
                soup = BeautifulSoup(html, "html.parser")
                text = soup.get_text()
                # Use regex to find temperatures
                temp_match = re.search(r"(-?\d+(?:,\d+)?)\s*°C", text)
                if temp_match:
                    data[field] = f"{temp_match.group(1).replace(',', '.')} °C"
                else:
                    # Fallback to label search
                    table = soup.find("table", class_="feldmitlabel")
                    if table:
                        tds = table.find_all("td")
                        if len(tds) >= 2:
                            data[field] = tds[1].get_text(strip=True)

        # 4. WGK (1100_1106)
        wgk_html = mapping.get("1100_1106")
        if wgk_html:
            soup = BeautifulSoup(wgk_html, "html.parser")
            text = soup.get_text()
            match = re.search(r"WGK\s*(\d+)", text, re.I)
            if match:
                data["wgk"] = f"WGK {match.group(1)}"
            elif "nicht wassergefährdend" in text.lower():
                data["wgk"] = "n.w.g."

        # 5. GHS / H / P (1100_1303)
        # ... stays mostly same, but make signal word extraction more robust
        ghs_html = mapping.get("1100_1303")
        if ghs_html:
            soup = BeautifulSoup(ghs_html, "html.parser")
            
            # Signal word
            text = soup.get_text()
            if "Gefahr" in text: data["signal_word"] = "Gefahr"
            elif "Achtung" in text: data["signal_word"] = "Achtung"

            # GHS Symbols
            for img in soup.find_all("img"):
                alt = img.get("alt", "")
                if alt.upper().startswith("GHS"):
                    data["ghs_symbols"].append(alt.lower())
            data["ghs_symbols"] = sorted(list(set(data["ghs_symbols"])))

            # H/P Phrases
            phrase_pattern = re.compile(r"([HP]\d{3}(?:\+[A-Z0-9]+)*)\s*[:]\s*(.*?)(?=\s*[HP]\d{3}|$)", re.DOTALL)
            for match in phrase_pattern.finditer(text):
                code, desc = match.group(1).strip(), match.group(2).strip()
                # Clean up description
                desc = re.split(r"\n", desc)[0].strip()
                if code.startswith("H"): data["h_phrases"].append({"id": code, "text": desc})
                elif code.startswith("P"): data["p_phrases"].append({"id": code, "text": desc})

        # 6. MAK / LD50 (robust search across common chapters)
        # MAK often in 1000_1001 or 1000_1002
        for key in ["1000_1001", "1000_1002"]:
            html = mapping.get(key)
            if html:
                text = BeautifulSoup(html, "html.parser").get_text(separator=" ")
                match = re.search(r"(\d+(?:,\d+)?)\s*(?:ml/m3|ppm|mg/m3)", text)
                if match:
                    data["mak"] = f"{match.group(1).replace(',', '.')} mg/m3"
                    break

        # LD50 often in 1200_1201 (Acute Toxicity)
        ld_html = mapping.get("1200_1201")
        if ld_html:
            text = BeautifulSoup(ld_html, "html.parser").get_text(separator=" ")
            match = re.search(r"LD50 oral Ratte\s*[:]?\s*(\d+)\s*mg/kg", text, re.I)
            if match:
                data["ld50"] = f"{match.group(1)} mg/kg"
            else:
                # Try more general LD50 search
                match = re.search(r"LD50\s*(?:oral|dermal)?\s*(?:Ratte|Rat|Maus|Mouse)?\s*[:]?\s*(\d+)\s*mg/kg", text, re.I)
                if match:
                    data["ld50"] = f"{match.group(1)} mg/kg"

        return data

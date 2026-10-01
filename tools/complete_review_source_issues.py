"""Derive source-issue contexts while preserving history and localization gaps."""
import hashlib
import json
import re


MANUAL = {
    "MR-SI001": ((83, 100), (83, 100)),
    "MR-SI002": ((90, 95), (89, 94)),
    "MR-SI003": ((110, 118), (109, 117)),
    "OLINC-035": ((40, 57), (43, 65)),
    "OLINC-072": ((137, 153), (178, 209)),
    "OLINC-112": ((65, 91), (65, 95)),
    "OLINC-115": ((9, 9), (9, 9)),
    "OLINC-119": ((49, 52), (55, 59)),
    "OLINC-239": ((100, 111), (185, 222)),
    "OLINC-242": ((31, 62), (54, 116)),
    "OLINC-365": ((136, 159), (262, 288)),
    "OLINC-380": ((27, 122), (40, 202)),
    "OLINC-382": ((55, 58), (96, 111)),
    "OLINC-431": ((110, 126), (119, 136)),
    "OLINC-453": ((117, 155), (132, 179)),
    "OLINC-456": ((114, 114), (114, 114)),
    "OLINC-459": ((84, 84), (91, 91)),
    "OLINC-461": ((82, 83), (89, 90)),
    "OLINC-462": ((125, 125), (125, 125)),
}


def derive(root, prov, manifest, edition, reader_bindings, locator):
    history_path = prov / "SOURCE_ISSUES.jsonl"
    history = [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    issues = {}
    for row in history:
        issues[row["issue"]["id"]] = row["issue"]
    assert len(history) == 656 and len(issues) == 655
    localized_path = root / "provenance/complete-v1.0/SOURCE_ISSUES_MR.jsonl"
    localized = {row["issue_id"]: row for row in
                 map(json.loads, localized_path.read_text(encoding="utf-8").splitlines())} if localized_path.exists() else {}
    for uid, unit in manifest.items():
        text = (root / "mr" / unit["source_path"]).read_text(encoding="utf-8")
        for note in re.findall(r"(?m)^\s*%READERNOTE\{(.*)\}\s*$", text):
            for iid in re.findall(r"[A-Z]+(?:-[A-Z]+)?-?\d{3}", note):
                if iid in issues and iid not in localized:
                    localized[iid] = {"issue_id": iid, "rationale_mr": note,
                                      "derivation": "मराठी स्रोतफाइलमधील आधीची स्पष्ट READERNOTE; नवा स्रोतदोष दावा नाही"}
    assert set(localized) <= set(issues)
    localized_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in localized.values()), encoding="utf-8")
    evidence = {"path_or_uri": "provenance/SOURCE_ISSUES.jsonl", "sha256": hashlib.sha256(history_path.read_bytes()).hexdigest()}
    canonical, legacy, occurrences, markdown, missing, repairs = [], [], [], [], [], []
    aligned_contexts, aligned_cache = [], {}

    def aligned_target_span(uid, source_path, target_path, source_span, iid):
        if uid not in aligned_cache:
            both = []
            for path in (source_path, target_path):
                text = (root / path).read_text(encoding="utf-8")
                positions, cursor = [], 0
                for block in re.split(r"\n\s*\n", text.strip()):
                    begin = text.find(block, cursor)
                    assert begin >= 0, (uid, path, "aligned block missing")
                    end = begin + len(block)
                    positions.append((text.count("\n", 0, begin) + 1,
                                      text.count("\n", 0, end) + 1))
                    cursor = end
                both.append(positions)
            assert len(both[0]) == len(both[1]), (uid, "aligned block counts differ")
            aligned_cache[uid] = both
        source, target = aligned_cache[uid]
        hits = [i for i, (start, end) in enumerate(source)
                if start <= source_span[1] and end >= source_span[0]]
        assert hits, (iid, uid, "source context has no aligned block")
        start, end = target[hits[0]][0], target[hits[-1]][1]
        aligned_contexts.append({"issue_id": iid, "unit_id": uid,
                                "source_lines": list(source_span[:2]),
                                "target_lines": [start, end],
                                "aligned_blocks": [i + 1 for i in hits]})
        return start, end, "गोठवलेल्या मूळ संदर्भाशी समान क्रमांकांचे पूर्ण aligned मराठी खंड; सद्य byte/line निर्देश प्रत्यक्ष पुन्हा मोजले. स्वतंत्र शब्दाच्या प्रत्येक वापराचा किंवा नवीन अर्थपुनर्वाचनाचा दावा नाही; ऐतिहासिक target locator SOURCE_ISSUES मध्ये राखला आहे"

    def span(iid, side, path, issue):
        text = (root / path).read_text(encoding="utf-8")
        count = len(text.splitlines())
        if iid in MANUAL:
            return (*MANUAL[iid][0 if side == "source" else 1], "प्रत्यक्ष गोठवलेला मूळ मजकूर आणि सद्य मराठी यांच्याशी पुनर्जुळवलेल्या संदर्भ-ओळी; जुना तपासनिर्देश इतिहासात राखला आहे")
        lookup = path.removeprefix("upstream/")
        declaration = issue.get(side + "_locator", "")
        match = re.search(re.escape(lookup) + r":([^;]+)", declaration)
        ranges = re.findall(r"(\d+)(?:[-–](\d+))?", match[1]) if match else []
        if ranges:
            start = min(int(a) for a, _ in ranges)
            end = max(int(b or a) for a, b in ranges)
            if 1 <= start <= end <= count:
                return start, end, "नोंदवलेल्या सर्व संबंधित ओळींचा सलग संदर्भ; स्वतंत्र शब्दाच्या प्रत्येक वापराचा दावा नाही"
        if side == "target":
            note_lines = [n for n, line in enumerate(text.splitlines(), 1) if "%READERNOTE{" in line and iid in line]
            if note_lines:
                return min(note_lines), max(note_lines), "दुरुस्ती स्पष्ट करणाऱ्या मूळ मराठी READERNOTE च्या प्रत्यक्ष ओळी"
        repairs.append({"issue_id": iid, "side": side, "historical_locator": declaration,
                        "current_path": path, "current_lines": count})
        return 1, count, "ऐतिहासिक सूक्ष्म ओळी जुळत नसल्याने संपूर्ण एककाचे अचूक बाइट-ओळी दिले आहेत; जुना निर्देश SOURCE_ISSUES मध्ये राखला आहे"

    for iid, issue in issues.items():
        uid = issue["unit_id"]
        assert uid in manifest
        source_path = "upstream/" + manifest[uid]["source_path"]
        target_path = "mr/" + manifest[uid]["source_path"]
        source_span = span(iid, "source", source_path, issue)
        target_span = aligned_target_span(uid, source_path, target_path, source_span, iid)
        reason = localized.get(iid, {}).get("rationale_mr")
        if not reason:
            missing.append(iid)
            reason = issue.get("finding") or issue.get("exact_condition") or issue.get("classification") or issue.get("reader_note")
        assert reason
        question = localized.get(iid, {}).get("review_question_mr") or (
            f"{iid} मधील खाली दिलेल्या मूळ आणि मराठी ओळींची तुलना करा: दुरुस्ती, खुलासा किंवा समतुल्य मांडणीने गणितीय अर्थ आणि नोंदवलेली अनिश्चितता योग्य राखली आहे का? आवश्यक असल्यास नेमके सुधारित मराठी रूप द्या.")
        oid = f"{iid}-{uid}"
        source = locator(source_path, uid, *source_span[:2], iid, reason, source_span[2])
        target = locator(target_path, uid, *target_span[:2], iid, reason, target_span[2])
        assert source["file_sha256"] == manifest[uid]["source_sha256"]
        chosen = f"{target_path}:{target_span[0]}–{target_span[1]} मधील नोंदवलेले मराठी रूप; पूर्ण अचूक उतारा खाली आहे"
        context = {"occurrence_id": oid, "unit_id": uid, "semantic_unit_id": "source-issue:" + iid,
                   "source": source, "target": target, "reader_locator": reader_bindings[uid], "evidence_refs": [evidence]}
        canonical.append({"decision_id": iid, "record_kind": "notation" if localized.get(iid, {}).get("reporting_lane") == "suggested_improvement" else "source_correction", "recording_mode": "derived",
                          "edition": edition, "source_term_or_construction": iid + ": " + (localized.get(iid, {}).get("current_classification") or issue.get("classification") or "source observation"),
                          "intended_sense": reason, "chosen_rendering": chosen, "rationale": reason,
                          "authorities_checked": [{"authority_id": "OpenLogic-frozen-source", "citation": "गोठवलेल्या मूळ स्रोताची आणि मराठीची तुलना",
                                                   "passage_id": "source-issue:" + iid + ":source-context",
                                                   "passage_sha256": hashlib.sha256(source["excerpt"].encode("utf-8")).hexdigest(),
                                                   "locator": source_path, "source_sha256": source["file_sha256"], "status": "checked_context_only",
                                                   "note": "passage_sha256 हा खाली दिलेल्या नेमक्या मूळ source.excerpt च्या UTF-8 बाइट्सचा हॅश आहे. मूळ तपासनोंद आणि तिचा इतिहास स्वतंत्र SOURCE_ISSUES.jsonl मध्ये आहे. काही नोंदी समतुल्य मांडणी किंवा मागे घेतलेले दोष-दावे आहेत; सर्व नोंदींना निश्चित मूळ गणितीय त्रुटी मानलेले नाही."}],
                          "alternatives": [], "confidence": "medium", "confidence_reason": "पूर्वीच्या स्रोततुलनेवरून व्युत्पन्न संदर्भ; स्वतंत्र मानवी स्वीकृती नाही.",
                          "provisional": True, "review_priority": "high", "expert_review_useful": True,
                          "expert_review_reason": "प्रत्यक्ष दुरुस्ती, तिची मर्यादा आणि मूळ गणितीय अर्थ पुनर्तपासण्यासाठी.",
                          "please_double_check_question": question, "occurrences": [context]})
        legacy.append({"schema": "openlogic-expert-review-decision/1", "record_kind": "source_correction_or_observation",
                       "issue_id": iid, "unit_id": uid, "rationale": reason, "precise_review_question": question,
                       "chosen_action": chosen, "occurrence_ids": [oid], "historical_issue": issue, "open_to_correction": True})
        binding = reader_bindings[uid]
        occurrences.append({"schema": "openlogic-expert-review-occurrence/1", "occurrence_id": oid, "decision_id": iid,
                            "record_kind": "source_correction_or_observation", "unit_id": uid, "source_path": source_path,
                            "source_lines": f"{source_span[0]}-{source_span[1]}", "target_path": target_path,
                            "target_lines": f"{target_span[0]}-{target_span[1]}", "choice_locator_precision": source_span[2] + "; " + target_span[2],
                            "chosen_rendering": chosen, "rationale": reason, "please_double_check_question": question,
                            "script": "Deva", "locale": "mr-IN", "reader_pdf_sha256": binding["artifact_sha256"],
                            "reader_pdf_pages": [binding["assembled_pdf_page"]], "reader_page_label": binding["printed_page"],
                            "page_locator_precision": binding["provenance"]})
        markdown += [f"## {iid} — {uid}", "", reason, "", chosen, "", question, "",
                     f"मूळ: {source_path}:{source_span[0]}–{source_span[1]}; मराठी: {target_path}:{target_span[0]}–{target_span[1]}.", "",
                     source_span[2] + "; " + target_span[2] + ".", ""]
    return canonical, legacy, occurrences, markdown, missing, {
        "source_issue_history_rows": len(history), "source_issue_decisions": len(issues),
        "localized_source_issues": len(issues) - len(missing), "missing_source_issue_localization": missing,
        "source_issue_locator_fallbacks": repairs,
        "source_issue_aligned_target_contexts": aligned_contexts,
    }

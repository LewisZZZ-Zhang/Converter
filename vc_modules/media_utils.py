def format_bitrate(raw_bitrate):
    if not raw_bitrate:
        return ""
    try:
        return f"{int(raw_bitrate) // 1000} kbps"
    except Exception:
        return str(raw_bitrate)


def parse_frame_rate(raw_frame_rate):
    try:
        if raw_frame_rate and "/" in raw_frame_rate:
            num, den = raw_frame_rate.split("/")
            den_value = float(den)
            return float(num) / den_value if den_value != 0 else 0
        return float(raw_frame_rate) if raw_frame_rate else 0
    except Exception:
        return 0


def infer_hdr_info(stream):
    side_data_list = stream.get("side_data_list", []) or []
    color_transfer = (stream.get("color_transfer") or "").lower()
    color_primaries = (stream.get("color_primaries") or "").lower()
    color_space = (stream.get("color_space") or "").lower()

    hdr_tags = []
    dolby_vision = None

    has_mastering = any(
        (side_data.get("side_data_type") or "").lower() == "mastering display metadata"
        for side_data in side_data_list
    )
    has_cll = any(
        (side_data.get("side_data_type") or "").lower() == "content light level metadata"
        for side_data in side_data_list
    )
    has_hdr10_plus = any(
        "2094-40" in (side_data.get("side_data_type") or "").lower()
        or "hdr10+" in (side_data.get("side_data_type") or "").lower()
        for side_data in side_data_list
    )

    dovi_side_data = next(
        (
            side_data
            for side_data in side_data_list
            if "dovi" in (side_data.get("side_data_type") or "").lower()
            or "dolby vision" in (side_data.get("side_data_type") or "").lower()
        ),
        None,
    )

    if dovi_side_data:
        profile = dovi_side_data.get("dv_profile")
        level = dovi_side_data.get("dv_level")
        el_present = (
            dovi_side_data.get("el_present_flag")
            or dovi_side_data.get("dv_el_present_flag")
            or dovi_side_data.get("el_present")
        )
        rpu_present = (
            dovi_side_data.get("rpu_present_flag")
            or dovi_side_data.get("dv_rpu_present_flag")
            or dovi_side_data.get("rpu_present")
        )
        bl_present = (
            dovi_side_data.get("bl_present_flag")
            or dovi_side_data.get("dv_bl_present_flag")
            or dovi_side_data.get("bl_present")
        )

        dv_parts = ["Dolby Vision"]
        if profile is not None:
            dv_parts.append(f"P{profile}")
        if level is not None:
            dv_parts.append(f"L{level}")
        if el_present:
            dv_parts.append("EL")
        elif bl_present or rpu_present:
            dv_parts.append("BL")
        if rpu_present:
            dv_parts.append("RPU")
        dolby_vision = " ".join(dv_parts)
        hdr_tags.append(dolby_vision)

    if has_hdr10_plus:
        hdr_tags.append("HDR10+")
    elif color_transfer == "smpte2084":
        if has_mastering or has_cll:
            hdr_tags.append("HDR10")
        else:
            hdr_tags.append("PQ HDR")
    elif color_transfer == "arib-std-b67":
        hdr_tags.append("HLG")
    elif color_primaries == "bt2020" or color_space.startswith("bt2020"):
        hdr_tags.append("BT.2020")

    if not hdr_tags:
        hdr_tags.append("SDR")

    # Keep order stable but unique.
    unique_tags = []
    for tag in hdr_tags:
        if tag not in unique_tags:
            unique_tags.append(tag)

    return {
        "tags": unique_tags,
        "dolby_vision": dolby_vision,
        "has_mastering_metadata": has_mastering,
        "has_content_light_metadata": has_cll,
    }


def build_video_stream_desc(stream):
    idx = stream.get("index", -1)
    codec = stream.get("codec_name", "未知")
    lang = stream.get("tags", {}).get("language", "")
    frame_rate = parse_frame_rate(stream.get("r_frame_rate", ""))
    width = stream.get("width", "")
    height = stream.get("height", "")
    bitrate = stream.get("bit_rate", "") or stream.get("tags", {}).get("BPS", "")
    bitrate_text = format_bitrate(bitrate)
    hdr_info = infer_hdr_info(stream)
    hdr_text = " / ".join(hdr_info["tags"])

    parts = [f"#{idx}", codec]
    if lang:
        parts.append(lang)
    if width and height:
        parts.append(f"{width}x{height}")
    parts.append(f"{frame_rate:.2f}fps")
    if bitrate_text:
        parts.append(bitrate_text)
    if hdr_text:
        parts.append(f"[{hdr_text}]")

    return " ".join(parts).strip()


def build_audio_stream_desc(stream):
    idx = stream.get("index", -1)
    codec = stream.get("codec_name", "未知")
    lang = stream.get("tags", {}).get("language", "")
    sample_rate = stream.get("sample_rate", "")
    channels = stream.get("channels", "")
    bitrate = stream.get("bit_rate", "") or stream.get("tags", {}).get("BPS", "")
    bitrate_text = format_bitrate(bitrate)

    parts = [f"#{idx}", codec]
    if lang:
        parts.append(lang)
    if sample_rate:
        parts.append(f"{sample_rate}Hz")
    if channels:
        parts.append(f"{channels}ch")
    if bitrate_text:
        parts.append(bitrate_text)
    return " ".join(parts).strip()


def build_subtitle_stream_desc(stream):
    idx = stream.get("index", -1)
    codec = stream.get("codec_name", "未知")
    lang = stream.get("tags", {}).get("language", "")
    parts = [f"#{idx}", codec]
    if lang:
        parts.append(lang)
    return " ".join(parts).strip()


def build_summary(info_streams, info_format):
    overall_bitrate = info_format.get("format", {}).get("bit_rate", "")
    overall_bitrate_disp = format_bitrate(overall_bitrate)

    width = height = pix_fmt = color_depth = ""
    hdr_tags = []
    for stream in info_streams.get("streams", []):
        if stream.get("codec_type") == "video":
            width = stream.get("width", "")
            height = stream.get("height", "")
            pix_fmt = stream.get("pix_fmt", "")
            color_depth = stream.get("bits_per_raw_sample", "")
            hdr_tags = infer_hdr_info(stream)["tags"]
            break

    if not color_depth and pix_fmt:
        pix_fmt_map = {
            "yuv420p": "8",
            "yuv422p": "8",
            "yuv444p": "8",
            "yuv420p10le": "10",
            "yuv422p10le": "10",
            "yuv444p10le": "10",
            "yuv420p12le": "12",
            "yuv422p12le": "12",
            "yuv444p12le": "12",
        }
        color_depth = pix_fmt_map.get(pix_fmt, "")

    parts = []
    if overall_bitrate_disp:
        parts.append(f"总比特率: {overall_bitrate_disp}")
    if width and height:
        parts.append(f"分辨率: {width}x{height}")
    if color_depth:
        parts.append(f"色深: {color_depth}bit")
    if pix_fmt:
        parts.append(f"像素格式: {pix_fmt}")
    if hdr_tags:
        parts.append(f"HDR: {' / '.join(hdr_tags)}")
    return "  ".join(parts)

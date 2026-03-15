from __future__ import annotations

import datetime as _dt
import uuid as _uuid
import zipfile as _zip
from pathlib import Path


NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _xml_decl() -> str:
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'


def _content_types(num_slides: int) -> str:
    overrides = []
    for i in range(1, num_slides + 1):
        overrides.append(
            f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        )
    return (
        _xml_decl()
        + """
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
"""
        + "\n".join(f"  {x}" for x in overrides)
        + """
</Types>
"""
    ).strip()


def _rels_root() -> str:
    return (
        _xml_decl()
        + """
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""
    ).strip()


def _presentation_xml(num_slides: int) -> str:
    slide_ids = []
    rel_ids = []
    for i in range(1, num_slides + 1):
        slide_ids.append(f'<p:sldId id="{256 + i}" r:id="rId{i}"/>')
        rel_ids.append(
            f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
        )
    return (
        _xml_decl()
        + f"""
<p:presentation xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">
  <p:sldMasterIdLst>
    <p:sldMasterId id="2147483648" r:id="rId{num_slides + 1}"/>
  </p:sldMasterIdLst>
  <p:sldIdLst>
    {' '.join(slide_ids)}
  </p:sldIdLst>
  <p:sldSz cx="12192000" cy="6858000" type="screen16x9"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>
"""
    ).strip()


def _presentation_rels(num_slides: int) -> str:
    rels = []
    for i in range(1, num_slides + 1):
        rels.append(
            f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
        )
    rels.append(
        f'<Relationship Id="rId{num_slides + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
    )
    return (
        _xml_decl()
        + """
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
"""
        + "\n".join(f"  {x}" for x in rels)
        + """
</Relationships>
"""
    ).strip()


def _slide_master_xml() -> str:
    # Minimal master with one layout.
    return (
        _xml_decl()
        + f"""
<p:sldMaster xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:sldLayoutIdLst>
    <p:sldLayoutId id="2147483649" r:id="rId1"/>
  </p:sldLayoutIdLst>
  <p:txStyles/>
</p:sldMaster>
"""
    ).strip()


def _slide_master_rels() -> str:
    return (
        _xml_decl()
        + """
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>
"""
    ).strip()


def _slide_layout_xml() -> str:
    return (
        _xml_decl()
        + f"""
<p:sldLayout xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}" type="titleAndObj" preserve="1">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
    </p:spTree>
  </p:cSld>
</p:sldLayout>
"""
    ).strip()


def _slide_layout_rels() -> str:
    return (
        _xml_decl()
        + """
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>
"""
    ).strip()


def _theme_xml() -> str:
    # Extremely minimal theme; enough for most viewers.
    return (
        _xml_decl()
        + f"""
<a:theme xmlns:a="{NS_A}" name="Office Theme">
  <a:themeElements>
    <a:clrScheme name="Office">
      <a:dk1><a:srgbClr val="000000"/></a:dk1>
      <a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>
      <a:dk2><a:srgbClr val="1F1F1F"/></a:dk2>
      <a:lt2><a:srgbClr val="F3F3F3"/></a:lt2>
      <a:accent1><a:srgbClr val="4F46E5"/></a:accent1>
      <a:accent2><a:srgbClr val="0EA5E9"/></a:accent2>
      <a:accent3><a:srgbClr val="22C55E"/></a:accent3>
      <a:accent4><a:srgbClr val="EAB308"/></a:accent4>
      <a:accent5><a:srgbClr val="F97316"/></a:accent5>
      <a:accent6><a:srgbClr val="EF4444"/></a:accent6>
      <a:hlink><a:srgbClr val="2563EB"/></a:hlink>
      <a:folHlink><a:srgbClr val="7C3AED"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="Office">
      <a:majorFont><a:latin typeface="Calibri"/></a:majorFont>
      <a:minorFont><a:latin typeface="Calibri"/></a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name="Office"/>
  </a:themeElements>
</a:theme>
"""
    ).strip()


def _paragraph(
    text: str,
    *,
    font_size: int,
    bullet: bool,
    bold: bool = False,
    center: bool = False,
    color: str = "E2E8F0",
) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    bu = "<a:buChar char=\"•\"/>" if bullet else "<a:buNone/>"
    algn = "ctr" if center else "l"
    run_b = "1" if bold else "0"
    ppr = (
        f'<a:pPr algn="{algn}" marL="457200" indent="-228600">{bu}</a:pPr>'
        if bullet
        else f'<a:pPr algn="{algn}">{bu}</a:pPr>'
    )
    return f"""
      <a:p>
        {ppr}
        <a:r>
          <a:rPr lang="en-US" sz="{font_size}" b="{run_b}">
            <a:solidFill><a:srgbClr val="{color}"/></a:solidFill>
          </a:rPr>
          <a:t>{_escape(t)}</a:t>
        </a:r>
      </a:p>
""".rstrip()


def _shape_textbox(
    shape_id: int,
    name: str,
    x: int,
    y: int,
    cx: int,
    cy: int,
    paras: list[str],
    *,
    font_size: int,
    bullet: bool,
    geom: str = "rect",
    fill: str | None = None,
    line: str | None = None,
    alpha: int | None = None,
    bold: bool = False,
    center: bool = False,
    title_color: str = "F8FAFC",
    text_color: str = "E2E8F0",
) -> str:
    fill_xml = "<a:noFill/>"
    if fill:
        a = f'<a:alpha val="{alpha}"/>' if alpha is not None else ""
        fill_xml = f"<a:solidFill><a:srgbClr val=\"{fill}\">{a}</a:srgbClr></a:solidFill>"

    line_xml = "<a:ln><a:noFill/></a:ln>"
    if line:
        line_xml = f"<a:ln w=\"12700\"><a:solidFill><a:srgbClr val=\"{line}\"/></a:solidFill></a:ln>"

    paragraphs_xml = []
    for i, p in enumerate(paras):
        is_bullet = bullet and i > 0
        paragraphs_xml.append(
            _paragraph(
                p,
                font_size=font_size,
                bullet=is_bullet,
                bold=(bold and i == 0),
                center=(center and i == 0),
                color=(title_color if i == 0 else text_color),
            )
        )
    paras_xml = "\n".join([x for x in paragraphs_xml if x.strip()])

    return (
        f"""
    <p:sp>
      <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="{_escape(name)}"/>
        <p:cNvSpPr txBox="1"/>
        <p:nvPr/>
      </p:nvSpPr>
      <p:spPr>
        <a:xfrm>
          <a:off x="{x}" y="{y}"/>
          <a:ext cx="{cx}" cy="{cy}"/>
        </a:xfrm>
        <a:prstGeom prst="{geom}"><a:avLst/></a:prstGeom>
        {fill_xml}
        {line_xml}
      </p:spPr>
      <p:txBody>
        <a:bodyPr wrap="square"/>
        <a:lstStyle/>
{paras_xml}
      </p:txBody>
    </p:sp>
"""
    ).rstrip()

def _shape_rect(shape_id: int, name: str, x: int, y: int, cx: int, cy: int, *, fill: str, alpha: int | None = None) -> str:
    a = f'<a:alpha val="{alpha}"/>' if alpha is not None else ""
    return (
        f"""
    <p:sp>
      <p:nvSpPr>
        <p:cNvPr id="{shape_id}" name="{_escape(name)}"/>
        <p:cNvSpPr/>
        <p:nvPr/>
      </p:nvSpPr>
      <p:spPr>
        <a:xfrm>
          <a:off x="{x}" y="{y}"/>
          <a:ext cx="{cx}" cy="{cy}"/>
        </a:xfrm>
        <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
        <a:solidFill><a:srgbClr val="{fill}">{a}</a:srgbClr></a:solidFill>
        <a:ln><a:noFill/></a:ln>
      </p:spPr>
    </p:sp>
"""
    ).rstrip()


def _slide_xml(title: str, bullets: list[str]) -> str:
    # Coordinates are in EMUs; these are rough but readable defaults.
    bg = _shape_rect(2, "Background", 0, 0, 12192000, 6858000, fill="0B1220")
    accent = _shape_rect(3, "AccentBar", 0, 0, 304800, 6858000, fill="4F46E5")
    icon = _shape_textbox(
        4,
        "Icon",
        x=11000000,
        y=380000,
        cx=650000,
        cy=650000,
        paras=["S"],
        font_size=2400,
        bullet=False,
        geom="ellipse",
        fill="1F2A44",
        line="334155",
        bold=True,
        center=True,
    )
    title_box = _shape_textbox(
        2,
        "Title",
        x=685800,
        y=342900,
        cx=10820400,
        cy=914400,
        paras=[title],
        font_size=3600,
        bullet=False,
        bold=True,
    )
    body_box = _shape_textbox(
        5,
        "Body",
        x=685800,
        y=1500000,
        cx=10820400,
        cy=4700000,
        paras=["Key points"] + bullets,
        font_size=2200,
        bullet=True,
        geom="roundRect",
        fill="0F172A",
        line="1E293B",
        alpha=98000,
    )
    return (
        _xml_decl()
        + f"""
<p:sld xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
{bg}
{accent}
{icon}
{title_box}
{body_box}
    </p:spTree>
  </p:cSld>
</p:sld>
"""
    ).strip()


def _slide_rels() -> str:
    return (
        _xml_decl()
        + """
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>
"""
    ).strip()


def _docprops_core() -> str:
    now = _dt.datetime.now(tz=_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return (
        _xml_decl()
        + f"""
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:dcmitype="http://purl.org/dc/dcmitype/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Safe and Sound — Demo Deck</dc:title>
  <dc:creator>Safe and Sound</dc:creator>
  <cp:lastModifiedBy>Safe and Sound</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>
"""
    ).strip()


def _docprops_app(num_slides: int) -> str:
    return (
        _xml_decl()
        + f"""
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Safe and Sound</Application>
  <Slides>{num_slides}</Slides>
  <Words>0</Words>
  <PresentationFormat>On-screen Show (16:9)</PresentationFormat>
  <Company></Company>
  <AppVersion>16.0000</AppVersion>
</Properties>
"""
    ).strip()


def _escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def build_deck(out_path: Path) -> None:
    slides = [
        (
            "Safe and Sound",
            [
                "Local-first privacy + sycophancy analysis from real chat exports",
                "Problem: users share sensitive info; assistants can be swayed into flipping answers without evidence",
                "Goal: make these risks visible and create reusable, anonymized benchmark data (SwayBench)",
            ],
        ),
        (
            "Who it’s for",
            [
                "Everyday AI users: understand what you shared and when the assistant changed its mind",
                "AI safety & eval builders: realistic disagreement→flip episodes (beyond synthetic prompts)",
                "Teams deploying assistants: quick audit of pushback vulnerability and risky advice shifts",
            ],
        ),
        (
            "What the app does",
            [
                "Upload a chat export (or use built-in example)",
                "Detect and anonymize PII/secrets (placeholders or safe synthetic replacements)",
                "Mine “pushback” moments (e.g., “that’s wrong”, “are you sure?”, leading “but”)",
                "Rank likely answer-changes after pushback (possible sycophancy/gullibility)",
                "Optional: web-grounded verification on anonymized snippets",
                "Export anonymized SwayBench JSONL for reuse and sharing",
            ],
        ),
        (
            "Privacy by design",
            [
                "Default: process locally in the browser — raw file never uploads",
                "Anonymization happens before any optional external verification",
                "Verification and sharing are opt-in, and only send anonymized snippets/items",
            ],
        ),
        (
            "Deliverables & impact",
            [
                "Working dashboard: privacy audit + pushback mining + answer-change review",
                "Reusable dataset: SwayBench JSONL (anonymized real-world pushback→change episodes)",
                "Helps users reduce privacy risk and helps researchers measure real-world sycophancy",
            ],
        ),
    ]

    num_slides = len(slides)
    tmp = out_path.with_suffix(f".{_uuid.uuid4().hex}.tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)

    with _zip.ZipFile(tmp, "w", compression=_zip.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _content_types(num_slides))
        z.writestr("_rels/.rels", _rels_root())

        z.writestr("ppt/presentation.xml", _presentation_xml(num_slides))
        z.writestr("ppt/_rels/presentation.xml.rels", _presentation_rels(num_slides))

        z.writestr("ppt/slideMasters/slideMaster1.xml", _slide_master_xml())
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", _slide_master_rels())

        z.writestr("ppt/slideLayouts/slideLayout1.xml", _slide_layout_xml())
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", _slide_layout_rels())

        z.writestr("ppt/theme/theme1.xml", _theme_xml())

        for i, (title, bullets) in enumerate(slides, start=1):
            z.writestr(f"ppt/slides/slide{i}.xml", _slide_xml(title, bullets))
            z.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", _slide_rels())

        z.writestr("docProps/core.xml", _docprops_core())
        z.writestr("docProps/app.xml", _docprops_app(num_slides))

    tmp.replace(out_path)


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "Safe_and_Sound_demo_deck.pptx"
    build_deck(out)
    print(str(out))


if __name__ == "__main__":
    main()

"""실제 약국 복약안내문 양식을 본떠 시험용 약봉지 그림과 정답을 만든다.

make_yakbong_samples.py보다 실제에 가깝게, 약국에서 흔히 보는 네 가지 양식을 그린다.
- classic: 약품사진 | 약품명+모양 | [효능 분류]+설명 | 1정씩3회4일분 (긴 이름은 '...'로 잘림)
- table:   노란 약품명 칸에 '이름[용량/1정]'이 두 줄로 꺾여 들어감 | 약효 > 분류 | 약품사진
- blue:    '*이름', '이름(성분', '이름_(1정)'처럼 약국이 덧붙인 글자, 옛 표기(캡셀, 밀리그람), 잘린 단위(500밀)
- card:    두 칸 카드(이름 + (분류)) + 왼쪽 영수증 칸에 작은 글씨 약 목록
모양 설명(흰색 서방정), 효능 분류([페니실린계 항생제]), 복약 그림 상자를 함께 그려 AI가 헷갈리게 한다.
각 양식을 스캔처럼 반듯한 것(scan)과 휴대폰으로 찍은 것처럼 기울고 그늘진 것(photo)으로 만든다.

정답(names)은 약국이 덧붙인 글자를 뺀 약 이름이다. 잘려서 끝이 안 보이는 이름은 '…'로 끝나고 앞부분만 맞으면 된다.
환자, 약국 정보는 모두 가짜이고 그림마다 '시험용 샘플'이라고 적는다.
실행: python scripts/make_yakbong_layouts.py  (Pillow와 한글 글꼴 필요)
"""
import csv
import os
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

OUT_DIR = "data/eval/yakbong_layouts"
ANSWERS = "data/eval/yakbong_layouts_answers.csv"
FONT_DIRS = ["/mnt/c/Windows/Fonts/", "C:/Windows/Fonts/"]

# 이름, 성분, 효능 분류, 모양, 설명
DRUGS = [
    ("동화록소닌정", "록소프로펜나트륨", "비스테로이드성 소염진통제", "담홍색의 원형 정제", "해열, 소염(염증 완화), 진통제"),
    ("소론도정", "프레드니솔론", "부신피질호르몬제", "백색의 원형 정제", "만성 염증, 피부질환, 알레르기질환 등"),
    ("뮤테란캡슐200밀리그램", "아세틸시스테인", "진해거담제 & 기침감기약", "백색의 분말이 충진된 경질캡슐", "가래를 묽게 하여 배출을 쉽게 해 주는 약"),
    ("유니레바정", "레바미피드", "기타 궤양치료제", "백색의 원형 필름코팅정", "위염, 위궤양 치료제"),
    ("타이레놀8시간이알서방정", "아세트아미노펜", "해열진통제", "흰색 서방정", "열을 내리고 통증을 줄여 주는 약"),
    ("코푸시럽", "디히드로코데인", "진해거담제", "적색 시럽제", "기침과 가래를 줄여 주는 약"),
    ("종근당아목시실린캡슐500밀리그램", "아목시실린수화물", "페니실린계 항생제", "주홍/황색 경질캡슐", "세균 감염을 치료하는 약"),
    ("디부루펜정400밀리그램", "덱시부프로펜", "소염진통제", "흰색 정제", "열을 내리고 염증과 통증을 줄여 주는 약"),
    ("알마겔정", "알마게이트", "제산제", "흰색의 원형 정제", "위산을 중화하여 속쓰림을 줄여 주는 약"),
    ("엘도스캡슐", "에르도스테인", "진해거담제", "초록/황색 경질캡슐", "가래를 묽게 하여 기침을 줄여 주는 약"),
    ("슈다페드정", "슈도에페드린염산염", "비염 & 코감기약", "백색의 원형 정제", "코막힘, 충혈 완화"),
    ("삼아케토티펜정", "케토티펜푸마르산염", "항히스타민 & 항알레르기약", "백색의 원형 정제", "알레르기 증상 완화"),
    ("몬테나츄정5밀리그램", "몬테루카스트나트륨", "류코트리엔 조절제", "분홍색의 원형 정제", "천식, 알레르기 비염 증상 완화"),
    ("리피토정10밀리그램", "아토르바스타틴칼슘", "이상지질혈증 치료제", "백색의 타원형 필름코팅정", "콜레스테롤을 낮추는 약"),
    ("베아제정", "판크레아틴", "소화효소제", "흰색의 원형 당의정", "소화불량 증상 완화"),
    ("경동아스피린장용정", "아스피린", "항혈전제", "백색의 원형 장용정", "혈전 생성을 막는 약"),
    ("애니코프캡슐300밀리그램", "테오브로민", "폐쇄성기도 치료제", "노랑/흰색 경질캡슐", "기관지를 넓혀 기침을 줄여 주는 약"),
    ("심바로드정20밀리그램", "심바스타틴", "이상지질혈증 치료제", "분홍색의 원형 정제", "콜레스테롤을 낮추는 약"),
]
DOSES = ["1정씩3회4일분", "1정씩2회4일분", "1캡슐씩3회4일분", "1정씩3회7일분", "1정씩1회7일분"]
STORE = ["기밀용기, 실온보관", "밀폐용기", "기밀용기", "차광밀폐용기, 실온(1~30℃)보관"]
INK, MUTED, LINE = (25, 25, 25), (80, 80, 80), (170, 175, 185)


def font(size, bold=False):
    name = "malgunbd.ttf" if bold else "malgun.ttf"
    for d in FONT_DIRS:
        if os.path.exists(d + name):
            return ImageFont.truetype(d + name, size)
    raise SystemExit("맑은 고딕 글꼴을 찾지 못했어요. FONT_DIRS를 고쳐 주세요.")


def short_mg(name):
    return name.replace("밀리그램", "mg")


def fit(draw, text, size, width, bold=True):
    """width에 안 들어가면 잘라서 '...'를 붙인다. (보이는 글자, 정답) 을 돌려준다."""
    f = font(size, bold)
    if draw.textlength(text, font=f) <= width:
        return text, text
    cut = text
    while cut and draw.textlength(cut + "...", font=f) > width:
        cut = cut[:-1]
    return cut + "...", cut + "…"


def wrap(draw, text, size, width, bold=False):
    f = font(size, bold)
    lines, line = [], ""
    for ch in text:
        if draw.textlength(line + ch, font=f) > width:
            lines.append(line)
            line = ch
        else:
            line += ch
    return lines + [line] if line else lines


def pills(draw, box, shape, rng):
    """약품사진 칸: 회색 바탕에 알약 두 개."""
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill=(205, 222, 235))
    for gx in range(x0, x1, 12):
        draw.line([gx, y0, gx, y1], fill=(195, 212, 226))
    color = (255, 255, 255)
    for word, c in [("담홍", (240, 200, 170)), ("분홍", (240, 190, 200)), ("주홍", (240, 140, 60)),
                    ("노랑", (245, 220, 90)), ("초록", (60, 120, 70)), ("적색", (200, 60, 60))]:
        if word in shape:
            color = c
    long = "캡슐" in shape or "서방" in shape or "타원" in shape
    w = (x1 - x0) // 2
    for k in range(2):
        cx, cy = x0 + w // 2 + k * w, (y0 + y1) // 2
        rx, ry = (w // 2 - 8, 13) if long else (17, 17)
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=color, outline=(150, 150, 150))


def icons(draw, x, y, n):
    """복약 그림 상자 (금지 표시)."""
    for k in range(n):
        bx = x + k * 52
        draw.rectangle([bx, y, bx + 46, y + 46], outline=(40, 60, 120), width=2)
        draw.ellipse([bx + 8, y + 6, bx + 38, y + 36], outline=(40, 60, 120), width=2)
        draw.line([bx + 12, y + 32, bx + 34, y + 10], fill=(40, 60, 120), width=2)


def header_info(draw, x, y, rng):
    draw.text((x, y), "환자정보: 홍길동(만40세/남)", font=font(20), fill=INK)
    draw.text((x + 420, y), f"조제일자: 2026-{rng.randint(1, 10):02d}-{rng.randint(1, 28):02d}", font=font(20), fill=INK)
    draw.text((x, y + 30), "약국: 약바로약국 (시험용 샘플)", font=font(20), fill=INK)


def classic(drugs, rng):
    row, width = 125, 1100
    img = Image.new("RGB", (width, 150 + row * len(drugs)), (248, 249, 252))
    d = ImageDraw.Draw(img)
    header_info(d, 20, 15, rng)
    d.rectangle([0, 85, width, 125], fill=(120, 170, 215))
    for x, t in [(40, "약품사진"), (220, "약품명"), (480, "복약안내"), (860, "투약량/보관")]:
        d.text((x, 92), t, font=font(20, True), fill="white")
    answers = []
    for i, (name, _, group, shape, desc) in enumerate(drugs):
        y = 135 + row * i
        d.line([0, y - 8, width, y - 8], fill=LINE, width=2)
        pills(d, (15, y + 10, 200, y + 100), shape, rng)
        shown, answer = fit(d, short_mg(name), 25, 245)
        answers.append(answer)
        d.text((220, y + 8), shown, font=font(25, True), fill=INK)
        for k, line in enumerate(wrap(d, shape, 18, 230)[:2]):
            d.text((220, y + 50 + k * 24), line, font=font(18), fill=MUTED)
        d.text((480, y + 8), f"[{group} ]", font=font(22, True), fill=INK)
        for k, line in enumerate(wrap(d, f"{group}: {desc}", 18, 340)[:2]):
            d.text((480, y + 45 + k * 24), line, font=font(18), fill=MUTED)
        d.text((860, y + 8), rng.choice(DOSES), font=font(18), fill=INK)
        for k, line in enumerate(wrap(d, rng.choice(STORE), 18, 220)[:2]):
            d.text((870, y + 45 + k * 24), line, font=font(18), fill=INK)
    return img, answers


def table(drugs, rng):
    row, width = 135, 1100
    img = Image.new("RGB", (width, 110 + row * len(drugs)), (252, 252, 250))
    d = ImageDraw.Draw(img)
    d.text((20, 15), "복약안내 (시험용 샘플) · 약바로약국", font=font(20), fill=INK)
    top = 60
    d.rectangle([0, top, width, top + 40], fill=(235, 235, 235), outline=LINE)
    for x, t in [(90, "약 품 명"), (520, "복 약 안 내"), (920, "약 품 사 진")]:
        d.text((x, top + 8), t, font=font(20), fill=INK)
    answers = []
    for i, (name, _, group, shape, desc) in enumerate(drugs):
        y = top + 40 + row * i
        d.rectangle([0, y, 290, y + row], fill=(250, 245, 190), outline=LINE)
        d.rectangle([290, y, 840, y + row], outline=LINE)
        d.rectangle([840, y, width, y + row], outline=LINE)
        unit = "1캡슐" if "캡슐" in name else ("10mL" if "시럽" in name else "1정")
        label = f"{short_mg(name)}[{rng.choice(['0.25g', '30mg', '68.1mg', '44.5mg', '5mg'])}/{unit}]"
        for k, line in enumerate(wrap(d, label, 21, 270, True)[:3]):
            d.text((10, y + 10 + k * 28), line, font=font(21, True), fill=INK)
        answers.append(short_mg(name))
        d.text((305, y + 10), f"약효 > {group}", font=font(20, True), fill=INK)
        for k, line in enumerate(wrap(d, desc + ". 증상이 심하면 전문가와 상의하세요.", 18, 520)[:3]):
            d.text((305, y + 45 + k * 26), line, font=font(18), fill=MUTED)
        pills(d, (860, y + 20, 1080, y + row - 20), shape, rng)
    return img, answers


def blue(drugs, rng):
    row, width = 150, 1100
    img = Image.new("RGB", (width, 120 + row * len(drugs)), (240, 244, 250))
    d = ImageDraw.Draw(img)
    d.text((20, 10), "약바로약국 (시험용 샘플)  TEL: 000-0000", font=font(20), fill=INK)
    d.rectangle([0, 50, width, 95], fill=(40, 110, 190))
    for x, t in [(30, "약품명"), (560, "복약안내"), (960, "투약량  횟수  일수")]:
        d.text((x, 58), t, font=font(20, True), fill="white")
    answers = []
    styles = ["star", "ingredient", "suffix", "old", "plain", "cut_unit"]
    rng.shuffle(styles)
    for i, (name, ingredient, group, shape, desc) in enumerate(drugs):
        y = 105 + row * i
        style = styles[i % len(styles)]
        core = name
        if style == "old":  # 옛 표기
            core = name.replace("캡슐", "캡셀").replace("밀리그램", "밀리그람")
        if style == "cut_unit" and "밀리그램" in name:
            core = name.replace("밀리그램", "밀")
        printed = {
            "star": f"*{core}",
            "ingredient": f"{core}({ingredient[:3]}",
            "suffix": f"*{core}_(1정)",
        }.get(style, core)
        shown, answer = fit(d, printed, 24, 300)
        if answer.endswith("…") and "(" not in shown and "_" not in shown:
            answers.append(answer.lstrip("*"))
        else:
            answers.append(core)
        d.text((25, y + 5), shown, font=font(24, True), fill=INK)
        d.text((25, y + 48), shape, font=font(18), fill=MUTED)
        d.text((25, y + 78), "(실온보관)", font=font(18), fill=INK)
        pills(d, (340, y + 15, 500, y + 75), shape, rng)
        icons(d, 515, y + 20, rng.choice([1, 2]))
        d.text((640, y + 5), f"({group})" if rng.random() < 0.5 else "", font=font(20, True), fill=INK)
        for k, line in enumerate(wrap(d, desc + ". 전문가와 상의 없이 장기간 연용하지 마세요.", 18, 330)[:3]):
            d.text((640, y + 38 + k * 25), line, font=font(18), fill=MUTED)
        d.text((990, y + 10), f"1     {rng.choice([2, 3])}     {rng.choice([3, 4, 7])}", font=font(20), fill=INK)
    return img, answers


def card(drugs, rng):
    cols, card_w, card_h = 2, 400, 210
    rows = (len(drugs) + 1) // 2
    width, top = 1100, 120
    img = Image.new("RGB", (width, top + rows * (card_h + 15) + 30), (250, 252, 248))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 260, img.height], fill=(120, 190, 80))
    d.text((15, 15), "약제비 계산서·영수증", font=font(18, True), fill="white")
    for k, t in enumerate(["환자성명 홍길동", "조제일자 2026-04-25", "본인부담금 3,000", "합계 3,000"]):
        d.text((15, 60 + k * 30), t, font=font(16), fill="white")
    d.text((15, 200), "약품명      투약량 횟수 일수", font=font(14), fill="white")
    for k, (name, *_ ) in enumerate(drugs):
        d.text((15, 225 + k * 22), f"{short_mg(name)[:12]}   1 3 3", font=font(14), fill="white")
    d.text((290, 20), "조제약&복약안내  (시험용 샘플)", font=font(28, True), fill=(40, 120, 40))
    d.text((290, 65), "환자정보: 홍길동 (남/만 34세)    약바로약국", font=font(18), fill=INK)
    answers = []
    for i, (name, _, group, shape, desc) in enumerate(drugs):
        cx = 280 + (i % cols) * (card_w + 15)
        cy = top + (i // cols) * (card_h + 15)
        d.rectangle([cx, cy, cx + card_w, cy + card_h], outline=(120, 190, 80), width=2)
        d.rectangle([cx, cy, cx + card_w, cy + 36], fill=(215, 238, 200))
        shown, answer = fit(d, short_mg(name), 19, 250)
        answers.append(answer)
        d.text((cx + 8, cy + 6), shown, font=font(19, True), fill=INK)
        tag = f"({group[:7]})"
        d.text((cx + card_w - 8 - d.textlength(tag, font=font(16)), cy + 9), tag, font=font(16), fill=INK)
        pills(d, (cx + 8, cy + 48, cx + 150, cy + 110), shape, rng)
        icons(d, cx + 8, cy + 125, 2)
        d.text((cx + 165, cy + 45), f"{shape[:9]} (실온보관)", font=font(15), fill=MUTED)
        for k, line in enumerate(wrap(d, "- " + desc + ". 증상이 심하면 전문가와 상의하세요.", 15, 225)[:5]):
            d.text((cx + 165, cy + 72 + k * 22), line, font=font(15), fill=INK)
    return img, answers


LAYOUTS = {"classic": classic, "table": table, "blue": blue, "card": card}


def _solve(a, b):
    """8x8 연립방정식 (가우스 소거). 원근 변환 계수를 구할 때 쓴다."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[p] = m[p], m[c]
        for r in range(n):
            if r != c:
                f = m[r][c] / m[c][c]
                m[r] = [x - f * y for x, y in zip(m[r], m[c])]
    return [m[i][n] / m[i][i] for i in range(n)]


def photo(img, rng):
    """휴대폰으로 찍은 것처럼: 원근으로 기울이고, 그늘과 구김을 넣고, 조금 흐리게."""
    w, h = img.size
    img = img.copy()
    d = ImageDraw.Draw(img)
    for _ in range(3):  # 구김
        y = rng.randint(h // 4, h - 20)
        pts = [(x, y + rng.randint(-15, 15)) for x in range(0, w + 100, 100)]
        d.line(pts, fill=(205, 205, 205), width=3)
        d.line([(x, yy + 3) for x, yy in pts], fill=(255, 255, 255), width=2)
    j = lambda s: rng.uniform(0, s)  # noqa: E731
    dst = [(j(0.06) * w, j(0.05) * h), (w - j(0.06) * w, j(0.05) * h),
           (w - j(0.04) * w, h - j(0.05) * h), (j(0.04) * w, h - j(0.05) * h)]
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    a, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        a += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        b += [u, v]
    img = img.transform((w, h), Image.PERSPECTIVE, _solve(a, b), Image.BICUBIC, fillcolor=(60, 55, 50))
    shade = Image.linear_gradient("L").rotate(rng.choice([0, 90, 180, 270])).resize((w, h))  # 돌린 뒤 늘려야 경계가 안 생긴다
    shade = shade.point(lambda v: 160 + v * 95 // 255).convert("RGB")
    img = ImageChops.multiply(img, shade)
    return img.filter(ImageFilter.GaussianBlur(1.0))


def main():
    rng = random.Random(11)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(ANSWERS, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["file", "layout", "variant", "names"])
        for layout, draw_fn in LAYOUTS.items():
            for n in (1, 2):
                drugs = rng.sample(DRUGS, rng.randint(4, 6))
                img, answers = draw_fn(drugs, rng)
                for variant, change, quality in [("scan", lambda im: im.filter(ImageFilter.GaussianBlur(0.4)), 85),
                                                 ("photo", lambda im: photo(im, rng), 55)]:
                    path = f"{OUT_DIR}/{layout}{n}_{variant}.jpg"
                    change(img).save(path, quality=quality)
                    writer.writerow([path, layout, variant, "|".join(answers)])
    print(f"양식 {len(LAYOUTS)}가지 x 2장 x 2가지 = {len(LAYOUTS) * 4}장을 {OUT_DIR}에 만들었어요")


if __name__ == "__main__":
    main()

"""약봉지 읽기 평가에 쓸 시험용 복약안내문 그림과 정답 파일을 만든다.

진짜 약봉지 사진은 개인정보와 저작권 문제가 있어서, 정답을 아는 가짜 복약안내문을 그린다.
약 이름은 다른 평가 파일에서 허가정보로 확인한 이름만 쓴다. 모양과 효능 글자는 그럴듯하게 지어낸 것이다.
같은 약봉지를 반듯함, 흐림, 기울임과 어두움, 작고 거칠게 네 가지로 만든다.
실행: python scripts/make_yakbong_samples.py  (Pillow와 한글 글꼴 필요)
"""
import csv
import os
import random

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

OUT_DIR = "data/eval/yakbong"
ANSWERS = "data/eval/yakbong_answers.csv"
FONTS = [  # 위에서부터 먼저 찾은 글꼴을 쓴다
    "/mnt/c/Windows/Fonts/malgun.ttf",
    "C:/Windows/Fonts/malgun.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
]

# 약 이름: (효능 분류, 효능 설명, 모양)
DRUGS = {
    "타이레놀정500밀리그람": ("해열진통제", "통증, 발열 완화", "흰색의 장방형 정제"),
    "베아제정": ("소화제", "소화불량 완화", "흰색의 원형 당의정"),
    "코니트라캡슐": ("항진균제", "무좀, 칸디다증 치료", "분홍색의 캡슐"),
    "심바로드정20밀리그램": ("고지혈증치료제", "콜레스테롤 저하", "분홍색의 원형 정제"),
    "휴심바정": ("고지혈증치료제", "콜레스테롤 저하", "흰색의 타원형 정제"),
    "초당아스피린장용정100mg": ("항혈전제", "혈전 생성 억제", "흰색의 원형 장용정"),
    "보령아스트릭스캡슐100밀리그람": ("항혈전제", "혈전 생성 억제", "흰색의 캡슐"),
    "부루펜정200밀리그램": ("소염진통제", "염증, 통증 완화", "흰색의 원형 정제"),
    "탁센연질캡슐": ("소염진통제", "통증 완화", "투명한 연질캡슐"),
    "게보린정": ("해열진통제", "두통, 치통 완화", "흰색의 원형 정제"),
    "펜잘큐정": ("해열진통제", "두통 완화", "흰색의 원형 정제"),
    "이지엔6애니연질캡슐": ("소염진통제", "통증 완화", "투명한 연질캡슐"),
    "이지엔6프로연질캡슐": ("소염진통제", "통증 완화", "투명한 연질캡슐"),
}
BAGS = [
    ["타이레놀정500밀리그람", "베아제정", "코니트라캡슐"],
    ["심바로드정20밀리그램", "초당아스피린장용정100mg", "보령아스트릭스캡슐100밀리그람", "베아제정"],
    ["부루펜정200밀리그램", "탁센연질캡슐", "게보린정"],
    ["휴심바정", "이지엔6프로연질캡슐", "펜잘큐정", "타이레놀정500밀리그람", "베아제정"],
    ["이지엔6애니연질캡슐", "코니트라캡슐"],
    ["게보린정", "초당아스피린장용정100mg", "심바로드정20밀리그램"],
]
HOW = ["1일 3회 식후 30분", "1일 2회 아침, 저녁 식후", "1일 1회 저녁 식후", "통증이 있을 때 1정"]
GREEN, LINE, INK = (110, 190, 90), (170, 170, 170), (30, 30, 30)


def font(size):
    for path in FONTS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    raise SystemExit("한글 글꼴을 찾지 못했어요. FONTS에 글꼴 경로를 넣어 주세요.")


def draw_bag(names, rng):
    width, row_h, top = 1000, 110, 230
    img = Image.new("RGB", (width, top + row_h * len(names) + 60), (250, 250, 246))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width, 70], fill=GREEN)
    d.text((30, 14), "조제약 복약안내", font=font(34), fill="white")
    d.text((700, 24), "시험용 샘플", font=font(22), fill="white")
    d.text((30, 90), "환자정보: 홍길동(만40세/남)", font=font(22), fill=INK)
    d.text((30, 125), "병원정보: 약바로의원", font=font(22), fill=INK)
    d.text((560, 90), "조제 약사: 김약사", font=font(22), fill=INK)
    d.text((560, 125), f"조제 일자: 2026-{rng.randint(1, 10):02d}-{rng.randint(1, 28):02d}", font=font(22), fill=INK)
    d.rectangle([0, 180, width, top - 6], fill=(225, 240, 215))
    for x, label in [(40, "약품사진"), (230, "약품명"), (560, "복약안내"), (860, "주의사항")]:
        d.text((x, 186), label, font=font(22), fill=(60, 110, 50))
    for i, name in enumerate(names):
        group, effect, shape = DRUGS[name]
        y = top + row_h * i
        d.line([0, y, width, y], fill=LINE, width=2)
        color = (240, 200, 210) if "분홍" in shape else (255, 255, 255)
        for k in range(2):
            d.ellipse([40 + k * 70, y + 30, 95 + k * 70, y + 85], fill=color, outline=LINE, width=2)
        d.text((230, y + 18), name, font=font(26 if len(name) < 14 else 22), fill=INK)
        d.text((230, y + 60), shape, font=font(19), fill=(90, 90, 90))
        d.text((560, y + 18), f"[{group}]", font=font(22), fill=INK)
        d.text((560, y + 55), f"{effect} / {rng.choice(HOW)}", font=font(19), fill=(70, 70, 70))
        d.text((860, y + 35), "졸음 주의" if rng.random() < 0.4 else "", font=font(18), fill=(200, 80, 60))
    return img


VARIANTS = {
    "clean": lambda img: img,
    "blur": lambda img: img.filter(ImageFilter.GaussianBlur(2.2)),
    "tilt_dark": lambda img: ImageEnhance.Brightness(
        img.rotate(8, expand=True, fillcolor=(40, 40, 40), resample=Image.BICUBIC)).enhance(0.55),
    "small": lambda img: img.resize((img.width * 2 // 5, img.height * 2 // 5)),
}


def main():
    rng = random.Random(7)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(ANSWERS, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["file", "variant", "names"])
        for n, names in enumerate(BAGS, start=1):
            base = draw_bag(names, rng)
            for variant, change in VARIANTS.items():
                path = f"{OUT_DIR}/bag{n}_{variant}.jpg"
                change(base).save(path, quality=30 if variant == "small" else 85)
                writer.writerow([path, variant, "|".join(names)])
    print(f"약봉지 {len(BAGS)}개 x {len(VARIANTS)}가지 = {len(BAGS) * len(VARIANTS)}장을 {OUT_DIR}에 만들었어요")


if __name__ == "__main__":
    main()

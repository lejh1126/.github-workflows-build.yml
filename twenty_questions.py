import tkinter as tk
from tkinter import messagebox
import random
import json
import os

from game_data import GAME_DATA, QUESTION_KEYWORDS


# ==================================================
# 1. 데이터 준비 (실제 항목/키워드는 game_data.py에서 수정)
# ==================================================

CATEGORIES = list(GAME_DATA.keys())

# 전체 문제 풀: 각 항목에 category를 붙여서 한 리스트로 합칩니다.
ALL_ITEMS = []
for _cat, _items in GAME_DATA.items():
    for _item in _items:
        ALL_ITEMS.append({**_item, "category": _cat})


def get_value(item, key):
    """항목이 해당 특징을 가지는지 반환. 주제 질문(동물/식물/인물)과 여성도 여기서 처리."""
    if key in CATEGORIES:
        return item["category"] == key

    if key == "여성":
        return item["category"] == "인물" and not item["features"].get("남성", False)

    return item["features"].get(key, False)


# ==================================================
# 2. 질문 인식
# ==================================================

NEGATIVE_WORDS = ["없", "아니", "않", "못"]


def find_question_key(question):
    """
    질문에서 가장 긴 키워드를 찾아 해당 특징 이름을 반환.
    '육식동물인가요?'에서 '동물'이 아니라 '육식동물'이 선택되도록
    딕셔너리 순서가 아닌 '가장 긴 일치'를 기준으로 합니다.
    """
    best = None  # (키워드 길이, 특징)

    for key, words in QUESTION_KEYWORDS.items():
        for word in words:
            if word in question and (best is None or len(word) > best[0]):
                best = (len(word), key)

    return best[1] if best else None


def check_data():
    """특징이 완전히 같은 항목이 있으면 질문만으로 구분할 수 없으므로 경고."""
    all_keys = list(QUESTION_KEYWORDS.keys())
    seen = {}

    for item in ALL_ITEMS:
        signature = tuple(get_value(item, k) for k in all_keys)
        if signature in seen:
            print(f"[경고] '{item['name']}'과(와) '{seen[signature]}'은(는) "
                  f"특징이 같아 질문으로 구분할 수 없습니다.")
        seen[signature] = item["name"]


# ==================================================
# 3. 난이도 / 설정
# ==================================================

DIFFICULTY = {
    "낮음": {"life": 5, "hint": 3},
    "중간": {"life": 3, "hint": 1},
    "어려움": {"life": 1, "hint": 0}
}

MAX_QUESTIONS = 20

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLLECTION_FILE = os.path.join(BASE_DIR, "collection.json")


# ==================================================
# 4. 메인 게임 클래스
# ==================================================

class TwentyQuestions:

    def __init__(self, root):

        self.root = root

        self.root.title("스무고개 게임")
        self.root.geometry("1050x780")
        self.root.minsize(850, 680)
        self.root.configure(bg="#F3EEDC")

        self.bg = "#F3EEDC"
        self.paper = "#FFFDF5"
        self.text_color = "#514B3E"
        self.green = "#819B75"
        self.red = "#C65D55"
        self.border = "#D6CDBB"

        self.level = ""
        self.answer = None

        self.life = 0
        self.hint_count = 0
        self.questions_left = MAX_QUESTIONS

        self.candidates = []
        self.used_questions = []

        self.reset_widget_refs()

        self.collection = self.load_collection()

        self.start_screen()

    def reset_widget_refs(self):
        self.life_label = None
        self.level_label = None
        self.gauge_canvas = None
        self.gauge_text = None
        self.hint_label = None
        self.result_label = None
        self.history = None
        self.right_life = None
        self.right_hint = None
        self.right_question = None
        self.question_entry = None
        self.answer_entry = None

    # ==================================================
    # 5. 도감 시스템
    # ==================================================

    def load_collection(self):

        if os.path.exists(COLLECTION_FILE):
            try:
                with open(COLLECTION_FILE, "r", encoding="utf-8") as file:
                    data = json.load(file)

                for category in CATEGORIES:
                    if category not in data:
                        data[category] = []

                return data

            except (json.JSONDecodeError, OSError):
                pass

        return {category: [] for category in CATEGORIES}

    def save_collection(self):

        try:
            with open(COLLECTION_FILE, "w", encoding="utf-8") as file:
                json.dump(self.collection, file, ensure_ascii=False, indent=4)
        except OSError:
            messagebox.showwarning("저장 실패", "도감을 저장하지 못했습니다.")

    def add_to_collection(self):
        """새로 등록되면 True, 이미 있으면 False."""

        name = self.answer["name"]
        category = self.answer["category"]

        if name not in self.collection[category]:
            self.collection[category].append(name)
            self.save_collection()
            return True

        return False

    # ==================================================
    # 6. 공통 화면 함수
    # ==================================================

    def clear_screen(self):

        for widget in self.root.winfo_children():
            widget.destroy()

        self.reset_widget_refs()

    def make_label(self, parent, text, size=12, bg=None, fg=None):

        return tk.Label(
            parent,
            text=text,
            font=("맑은 고딕", size, "bold"),
            bg=bg if bg else self.paper,
            fg=fg if fg else self.text_color,
            wraplength=450,
            justify="center"
        )

    def make_button(self, parent, text, command, color=None):

        return tk.Button(
            parent,
            text=text,
            font=("맑은 고딕", 11, "bold"),
            bg=color if color else self.paper,
            fg=self.text_color,
            activebackground=self.border,
            relief="flat",
            cursor="hand2",
            command=command
        )

    def add_history(self, text):

        self.history.insert(tk.END, text)
        self.history.see(tk.END)

    # ==================================================
    # 7. 시작 화면 (주제 선택 없이 바로 난이도 선택)
    # ==================================================

    def start_screen(self):

        self.clear_screen()

        frame = tk.Frame(self.root, bg=self.bg)
        frame.pack(expand=True)

        self.make_label(frame, "스무고개", 34, bg=self.bg).pack(pady=15)

        self.make_label(
            frame,
            "동물? 식물? 인물? 질문으로 정답을 좁혀 보세요!",
            14,
            bg=self.bg
        ).pack(pady=10)

        self.make_label(
            frame,
            f"질문은 최대 {MAX_QUESTIONS}번까지 할 수 있어요.",
            12,
            bg=self.bg
        ).pack(pady=5)

        self.make_label(frame, "난이도를 선택하세요", 17, bg=self.bg).pack(pady=15)

        for level, setting in DIFFICULTY.items():

            text = (
                f"{level} | 목숨 {setting['life']}개 | "
                f"힌트 {setting['hint']}개"
            )

            self.make_button(
                frame,
                text,
                lambda l=level: self.start_game(l)
            ).pack(fill="x", pady=6, ipady=8)

        self.make_button(
            frame, "나의 도감 보기", self.show_collection
        ).pack(pady=25, ipadx=15, ipady=5)

    # ==================================================
    # 8. 게임 시작
    # ==================================================

    def start_game(self, level):

        self.level = level

        setting = DIFFICULTY[level]

        self.life = setting["life"]
        self.hint_count = setting["hint"]
        self.questions_left = MAX_QUESTIONS

        self.answer = random.choice(ALL_ITEMS)

        self.candidates = ALL_ITEMS.copy()
        self.used_questions = []

        self.game_screen()

    # ==================================================
    # 9. 게임 화면
    # ==================================================

    def game_screen(self):

        self.clear_screen()

        header = tk.Frame(self.root, bg=self.bg)
        header.pack(fill="x", pady=8)

        self.make_label(header, "스무고개", 25, bg=self.bg).pack()

        top = tk.Frame(self.root, bg=self.bg)
        top.pack(fill="x", padx=25, pady=5)

        self.life_label = self.make_label(top, "", 17, bg=self.bg, fg=self.red)
        self.life_label.pack(side="left")

        self.level_label = self.make_label(
            top, f"난이도 : {self.level}", 15, bg=self.bg
        )
        self.level_label.pack(side="right")

        # 게이지
        gauge_frame = tk.Frame(
            self.root,
            bg=self.paper,
            highlightbackground=self.border,
            highlightthickness=1
        )
        gauge_frame.pack(fill="x", padx=30, pady=5)

        self.make_label(gauge_frame, "정답 근접도", 13).pack(pady=3)

        self.gauge_canvas = tk.Canvas(
            gauge_frame, height=18, bg="#E3DDCF", highlightthickness=0
        )
        self.gauge_canvas.pack(fill="x", padx=15, pady=3)
        # 창 크기가 정해지거나 바뀔 때마다 게이지를 다시 그립니다.
        self.gauge_canvas.bind("<Configure>", lambda e: self.update_gauge())

        self.gauge_text = self.make_label(gauge_frame, "0%", 11)
        self.gauge_text.pack(pady=3)

        # 중앙 영역
        content = tk.Frame(self.root, bg=self.bg)
        content.pack(fill="both", expand=True, padx=25, pady=5)

        # 왼쪽 힌트
        left = tk.Frame(
            content,
            bg=self.paper,
            width=175,
            highlightbackground=self.border,
            highlightthickness=1
        )
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        self.make_label(left, "HINT", 18).pack(pady=15)

        self.hint_label = self.make_label(left, "", 11)
        self.hint_label.pack(pady=5)

        self.make_button(
            left, "실루엣 힌트", lambda: self.use_hint("silhouette")
        ).pack(fill="x", padx=10, pady=8, ipady=5)

        self.make_button(
            left, "문장 힌트", lambda: self.use_hint("text")
        ).pack(fill="x", padx=10, pady=8, ipady=5)

        # 중앙 게임 공간
        center = tk.Frame(
            content,
            bg=self.paper,
            highlightbackground=self.border,
            highlightthickness=1
        )
        center.pack(side="left", fill="both", expand=True)

        self.make_label(center, "숨겨진 정답을 찾아보세요!", 16).pack(pady=(15, 5))

        self.make_label(
            center,
            "예) 동물인가요? / 날개가 있나요? / 가시가 있나요?",
            10
        ).pack()

        self.result_label = self.make_label(
            center, "질문을 입력하거나 정답을 추측해 보세요.", 12
        )
        self.result_label.pack(pady=10)

        list_frame = tk.Frame(center, bg=self.paper)
        list_frame.pack(fill="both", expand=True, padx=15, pady=10)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.history = tk.Listbox(
            list_frame,
            font=("맑은 고딕", 10),
            bg=self.paper,
            fg=self.text_color,
            relief="flat",
            selectbackground=self.green,
            yscrollcommand=scrollbar.set
        )
        self.history.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.history.yview)

        # 오른쪽 상태
        right = tk.Frame(
            content,
            bg=self.paper,
            width=140,
            highlightbackground=self.border,
            highlightthickness=1
        )
        right.pack(side="right", fill="y", padx=(10, 0))
        right.pack_propagate(False)

        self.make_label(right, "LEVEL", 16).pack(pady=15)
        self.make_label(right, self.level, 18, fg=self.green).pack(pady=10)

        self.right_life = self.make_label(right, "", 11)
        self.right_life.pack(pady=5)

        self.right_hint = self.make_label(right, "", 11)
        self.right_hint.pack(pady=5)

        self.right_question = self.make_label(right, "", 11)
        self.right_question.pack(pady=5)

        # 하단 입력창
        bottom = tk.Frame(self.root, bg=self.bg)
        bottom.pack(fill="x", padx=30, pady=(5, 3))

        self.make_label(bottom, "질문 입력", 10, bg=self.bg).pack(anchor="w")

        question_row = tk.Frame(bottom, bg=self.bg)
        question_row.pack(fill="x", pady=3)

        self.question_entry = tk.Entry(
            question_row,
            font=("맑은 고딕", 12),
            bg=self.paper,
            fg=self.text_color
        )
        self.question_entry.pack(
            side="left", fill="x", expand=True, ipady=9, padx=(0, 8)
        )
        self.question_entry.bind("<Return>", lambda e: self.submit_question())

        self.make_button(
            question_row, "질문하기", self.submit_question, self.green
        ).pack(side="right", ipadx=12, ipady=6)

        self.make_label(
            bottom, "정답 추측", 10, bg=self.bg
        ).pack(anchor="w", pady=(5, 0))

        answer_row = tk.Frame(bottom, bg=self.bg)
        answer_row.pack(fill="x", pady=3)

        self.answer_entry = tk.Entry(
            answer_row,
            font=("맑은 고딕", 12),
            bg=self.paper,
            fg=self.text_color
        )
        self.answer_entry.pack(
            side="left", fill="x", expand=True, ipady=9, padx=(0, 8)
        )
        self.answer_entry.bind("<Return>", lambda e: self.submit_guess())

        self.make_button(
            answer_row, "정답 제출", self.submit_guess, self.green
        ).pack(side="right", ipadx=12, ipady=6)

        self.make_button(
            self.root, "메인 화면", self.confirm_quit
        ).pack(pady=5)

        self.update_life()
        self.update_hint_display()
        self.update_question_display()
        self.update_gauge()

        self.root.update_idletasks()
        self.question_entry.focus_set()

    def confirm_quit(self):
        """진행 중인 게임에서 메인 화면으로 나갈 때 한 번 확인합니다."""
        if messagebox.askyesno("메인 화면", "게임을 끝내고 메인 화면으로 갈까요?"):
            self.start_screen()

    # ==================================================
    # 10. 상태 표시
    # ==================================================

    def update_life(self):

        if self.life_label is not None:
            self.life_label.config(text="♥ " * self.life)

        if self.right_life is not None:
            self.right_life.config(text=f"남은 목숨 : {self.life}")

    def update_hint_display(self):

        if self.hint_label is not None:
            self.hint_label.config(text=f"남은 힌트 : {self.hint_count}개")

        if self.right_hint is not None:
            self.right_hint.config(text=f"남은 힌트 : {self.hint_count}")

    def update_question_display(self):

        if self.right_question is not None:
            self.right_question.config(text=f"남은 질문 : {self.questions_left}")

    def update_gauge(self):

        if self.gauge_canvas is None or self.gauge_text is None:
            return

        total = len(ALL_ITEMS)
        remaining = len(self.candidates)

        if remaining <= 1:
            percent = 100
        else:
            percent = int((1 - remaining / total) * 100)

        percent = max(0, min(100, percent))

        # 글자는 캔버스 폭과 상관없이 항상 갱신
        self.gauge_text.config(text=f"{percent}%")

        width = self.gauge_canvas.winfo_width()

        if width <= 1:
            return

        self.gauge_canvas.delete("all")

        self.gauge_canvas.create_rectangle(
            0, 0, width, 18, fill="#E3DDCF", outline=""
        )
        self.gauge_canvas.create_rectangle(
            0, 0, width * percent / 100, 18, fill=self.green, outline=""
        )

    # ==================================================
    # 11. 질문 처리
    # ==================================================

    def submit_question(self):

        if self.question_entry is None:
            return

        question = self.question_entry.get().strip()

        if not question:
            return

        if self.questions_left <= 0:
            self.result_label.config(
                text="질문 기회를 모두 사용했습니다. 정답을 추측해 보세요!"
            )
            return

        self.question_entry.delete(0, tk.END)

        selected_key = find_question_key(question)

        if selected_key is None:
            self.result_label.config(
                text="인식할 수 없는 질문입니다. 예) 날개가 있나요? / 과일인가요?"
            )
            return

        if selected_key in self.used_questions:
            self.result_label.config(text="이미 질문한 내용입니다.")
            return

        self.used_questions.append(selected_key)
        self.questions_left -= 1

        answer_value = get_value(self.answer, selected_key)

        if any(word in question for word in NEGATIVE_WORDS):
            answer_value = not answer_value

        result = "네!" if answer_value else "아니요!"

        self.add_history(
            f"Q{MAX_QUESTIONS - self.questions_left}. {question}  →  {result}"
        )

        # 질문이 뒤집혔든 부정형이든, 걸러내는 기준은 '정답과 같은 특징값'입니다.
        feature_value = get_value(self.answer, selected_key)

        self.candidates = [
            item for item in self.candidates
            if get_value(item, selected_key) == feature_value
        ]

        self.result_label.config(text=f"{result} 질문에 대한 답변입니다.")

        self.update_question_display()
        self.update_gauge()

    # ==================================================
    # 12. 정답 제출
    # ==================================================

    def submit_guess(self):

        if self.answer_entry is None:
            return

        guess = self.answer_entry.get().strip()

        if not guess:
            return

        self.answer_entry.delete(0, tk.END)

        answer_names = [item["name"] for item in ALL_ITEMS]

        if guess == self.answer["name"]:
            self.correct_answer()

        elif guess in answer_names:
            self.add_history(f"오답 : {guess}")
            self.wrong_answer()

        else:
            self.result_label.config(
                text="등록되지 않은 정답입니다. 다시 입력해 주세요."
            )

    # ==================================================
    # 13. 힌트 사용
    # ==================================================

    def use_hint(self, hint_type):

        if self.hint_count <= 0:
            messagebox.showwarning("힌트 부족", "남은 힌트가 없습니다!")
            return

        self.hint_count -= 1

        if hint_type == "text":
            hint = self.answer["hint"]
            title = "문장 힌트"
        else:
            hint = self.answer["silhouette"]
            title = "실루엣 힌트"

        self.add_history(f"[{title}] {hint}")

        self.update_hint_display()

    # ==================================================
    # 14. 정답 / 오답 / 종료
    # ==================================================

    def correct_answer(self):

        used = MAX_QUESTIONS - self.questions_left
        is_new = self.add_to_collection()
        self.clear_screen()

        frame = tk.Frame(self.root, bg=self.bg)
        frame.pack(expand=True)

        self.make_label(
            frame, "정답!!", 35, bg=self.bg, fg=self.green
        ).pack(pady=20)

        image_area = tk.Frame(
            frame,
            bg=self.paper,
            width=400,
            height=260,
            highlightbackground=self.border,
            highlightthickness=1
        )
        image_area.pack(pady=15)
        image_area.pack_propagate(False)

        self.make_label(
            image_area,
            f"{self.answer['name']}\n\n이미지 연동 예정",
            20
        ).pack(expand=True)

        self.make_label(
            frame,
            f"정답 : {self.answer['name']} ({self.answer['category']})",
            20,
            bg=self.bg
        ).pack(pady=10)

        self.make_label(
            frame, f"사용한 질문 : {used}개", 13, bg=self.bg
        ).pack(pady=5)

        message = (
            "새로운 정답이 도감에 등록되었습니다!"
            if is_new else
            "이미 도감에 등록된 정답입니다."
        )

        self.make_label(
            frame, message, 13, bg=self.bg, fg=self.green
        ).pack(pady=10)

        self.make_button(
            frame, "다시 시작", self.start_screen
        ).pack(pady=15, ipadx=15, ipady=5)

    def wrong_answer(self):

        self.life -= 1
        self.update_life()

        if self.life <= 0:
            self.game_over()
        else:
            self.result_label.config(
                text="틀렸습니다! 목숨이 1개 감소했습니다."
            )

    def game_over(self):

        self.clear_screen()

        frame = tk.Frame(self.root, bg=self.bg)
        frame.pack(expand=True)

        self.make_label(
            frame, "GAME OVER", 32, bg=self.bg, fg=self.red
        ).pack(pady=20)

        self.make_label(
            frame,
            f"정답은 '{self.answer['name']}' ({self.answer['category']})입니다.",
            18,
            bg=self.bg
        ).pack(pady=15)

        self.make_button(
            frame, "다시 도전하기", self.start_screen
        ).pack(pady=15, ipadx=15, ipady=5)

    # ==================================================
    # 15. 도감 화면
    # ==================================================

    def show_collection(self):

        self.clear_screen()

        frame = tk.Frame(self.root, bg=self.bg)
        frame.pack(fill="both", expand=True, padx=30, pady=25)

        total_found = sum(len(self.collection.get(c, [])) for c in CATEGORIES)

        self.make_label(frame, "나의 도감", 28, bg=self.bg).pack(pady=10)

        self.make_label(
            frame,
            f"전체 {total_found} / {len(ALL_ITEMS)}",
            13,
            bg=self.bg
        ).pack()

        for category in CATEGORIES:

            items = self.collection.get(category, [])
            total = len(GAME_DATA[category])

            self.make_label(
                frame,
                f"{category} 도감 ({len(items)} / {total})",
                16,
                bg=self.bg
            ).pack(pady=(15, 5))

            names = ", ".join(items) if items else "아직 등록된 정답이 없습니다."

            self.make_label(frame, names, 11).pack()

        self.make_button(
            frame, "뒤로 가기", self.start_screen
        ).pack(pady=30, ipadx=15, ipady=5)


# ==================================================
# 16. 프로그램 실행
# ==================================================

if __name__ == "__main__":

    check_data()

    root = tk.Tk()

    game = TwentyQuestions(root)

    root.mainloop()

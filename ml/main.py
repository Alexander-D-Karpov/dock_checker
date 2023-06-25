import re
import math
import spacy
import pickle
import warnings
import Levenshtein
import numpy as np
import pandas as pd
import Levenshtein as lev

from catboost import Pool
from pdfminer.high_level import extract_pages
from tqdm import tqdm
from pdfminer.layout import LTTextContainer, LTChar


warnings.filterwarnings("ignore")


def extract_test_features(file):
    texts = []
    fonts = []
    squares = []
    ids = []
    coords = []
    relative_coords = []
    for page_layout in extract_pages(file):
        _x1, _y1, _x2, _y2 = page_layout.bbox
        for i, element in enumerate(page_layout):
            if isinstance(element, LTTextContainer):
                text = element.get_text().replace("\n", "")

                if "(cid:" in text:
                    return "Неправильная кодировка файла", False

                if text.split() != [] and len(text) > 4:
                    texts.append(text)

                    end = False
                    for text_line in element:
                        if end:
                            break
                        for character in text_line:
                            if isinstance(character, LTChar):
                                if "bold" in character.fontname.lower():
                                    fonts.append(1)
                                elif "italic" in character.fontname.lower():
                                    fonts.append(2)
                                else:
                                    fonts.append(0)
                                end = True
                                break

                    x1, y1, x2, y2 = element.bbox
                    coords.append([x1, y1, x2, y2])
                    relative_coords.append(
                        [x1 / _x2, y1 / _y2, (x2 - x1) / _x2, (y2 - y1) / _y2]
                    )

                    squares.append((int(x2) - int(x1)) * (int(y2) - int(y1)))

                    match = re.search(r"LTTextBoxHorizontal\((\d+)\)", str(element))
                    if match:
                        id = int(match.group(1))
                        ids.append(id)
        break

    if not texts:
        return "Файл состоит из сканов", False
    if len(texts) < 3:
        return "Главная страница состоит из сканов", False
    if len(texts) > 25:
        return "Произошла ошибка", False

    test_df = pd.DataFrame(
        {
            "text": texts,
            "font": fonts,
            "file": file,
            "squares": squares,
            "ids": ids,
            "coords": coords,
            "relative_coords": relative_coords,
        }
    )
    return test_df, True


def create_test_features(df):
    df["len_of_text"] = df["text"].apply(len)
    # df['len_of_text'] = df['text'].apply(lambda x: len(x.split()))

    df["rank"] = (
        df.groupby("file")["len_of_text"]
        .rank(ascending=False, method="min")
        .astype(int)
    )
    df["rank_squares"] = (
        df.groupby("file")["squares"].rank(ascending=False, method="min").astype(int)
    )
    df["font"] = df["font"].astype(
        object
    )  # Convert boolean to int for computation, True will be 1 and False will be 0
    df["bold"] = (df["font"] == 1).astype(int)
    df["bold_percentage"] = (
        df.groupby("file")["font"].transform(lambda x: x.mean() * 100).astype(int)
    )
    df["id_percentage"] = (
        df.groupby("file")["ids"].transform(lambda x: (x / x.max()) * 100).astype(int)
    )

    return df


def inference_models(checkpoint_name, test_df):
    columns_to_use = [
        "font",
        "rank",
        "rank_squares",
        "bold_percentage",
        "id_percentage",
    ]
    with open(checkpoint_name, "rb") as f:
        models = pickle.load(f)

    test_pool = Pool(data=test_df[columns_to_use])
    preds = []
    for model in models:
        preds.append(model.predict_proba(test_pool)[:, 1])
    test_df["pred"] = np.mean(preds, axis=0)
    return test_df, test_df.loc[test_df["pred"].idxmax(), "text"].strip()


def calculate_distances(target, list_of_strings, stride_fraction=1 / 4, threshold=0.3):
    target_length = len(target.split())
    min_distances = []

    stride_length = math.ceil(target_length * stride_fraction)

    for string in list_of_strings:
        all_distances = []
        string_words = string.split()

        if len(string_words) > target_length:
            i = 0
            while i < len(string_words) - target_length + 1:
                window = " ".join(string_words[i : i + target_length])

                distance = lev.distance(target, window) / len(target)
                if distance < threshold:
                    for j in range(
                        max(i - target_length, 0),
                        min(i + target_length, len(string_words) - target_length + 1),
                    ):
                        detailed_window = " ".join(string_words[j : j + target_length])
                        detailed_distance = lev.distance(target, detailed_window) / len(
                            target
                        )

                        all_distances.append((detailed_window, detailed_distance * 100))
                    i += stride_length
                else:
                    i += stride_length
        else:
            dist = lev.distance(target, string) / len(target)
            all_distances.append((string, dist * 100))

        if all_distances:
            min_window = min(all_distances, key=lambda x: x[1])
            min_distances.append([min_window[0], min_window[1]])

    return min_distances


def replace_multiple_spaces(text):
    return re.sub(" +", " ", text)


nlp = spacy.load("ru_core_news_sm")


def remove_special_characters(string):
    return re.sub(r"\W", "", string)


def difference_type(word1, word2):
    if word1 == word2:
        return None  # слова совпадают, пропускаем их

    if remove_special_characters(word1) == remove_special_characters(word2):
        return "Пропущен специцальный символ"

    if word1.lower() == word2.lower():
        return "Разная капитуляция слов"

    if word1.isdigit() and word2.isdigit():
        if abs(int(word1) - int(word2)) < 10:
            return "Небольшое числовое различие"
        else:
            return "Разные числа"

    token1 = nlp(word1)[0]
    token2 = nlp(word2)[0]
    if token1.lemma_ == token2.lemma_:
        if token1.pos_ != token2.pos_:
            return "Разные формы слова"
        else:
            return "Одинаковый корень, но разные формы"

    if Levenshtein.distance(word1, word2) <= 2:
        return "Возможная орфографическая ошибка или опечатка"
    return "Разные слова"


def compare_strings(str1, str2):
    words1 = str1.split()
    words2 = str2.split()

    words1_only = set(words1) - set(words2)
    words2_only = set(words2) - set(words1)

    differences = []
    mn_len = min(len(words1), len(words2))
    for i in range(mn_len):
        difference = difference_type(words1[i], words2[i])
        differences.append((words1[i], words2[i], difference))

    for word in words1_only:
        differences.append((word, None, "Word only in first string"))

    for word in words2_only:
        differences.append((None, word, "Word only in second string"))

    diff_types = set()
    for diff in differences:
        if diff[2]:
            diff_types.add(diff[2])

    return differences, diff_types


def get_matches(file, target):
    target = replace_multiple_spaces(target)

    result = []
    for i, page_layout in enumerate(tqdm(extract_pages(file))):
        _x1, _y1, _x2, _y2 = page_layout.bbox
        texts = []
        relative_coords = []
        d = {}
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                # print(element.get_text())
                x1, y1, x2, y2 = element.bbox
                raw = element.get_text()
                text = replace_multiple_spaces(raw.replace("\n", " ").strip())
                if len(text) > 3:
                    relative_coords.append(
                        ([x1 / _x2, y1 / _y2, (x2 - x1) / _x2, (y2 - y1) / _y2])
                    )
                    texts.append(text)
                    d[text] = raw

        distances = calculate_distances(target, texts)

        for window, distance in distances:
            if distance / len(target) < 0.2:
                # print(i)
                # print(window)
                for j in range(len(texts)):
                    if window in texts[j]:
                        raw_text = d[texts[j]]
                        rel_coord = relative_coords[j]
                        break
                difference, diff_types = compare_strings(window, target)
                result.append(
                    {
                        "page": i + 1,
                        "window": window,
                        "coordinates": rel_coord,
                        "distance": distance / len(target),
                        "diff_type": list(diff_types),
                        "raw_text": raw_text,
                    }
                )
    return result


# if __name__ == "__main__":
#     file = "some.pdf"
#     columns_to_use = [
#         "font",
#         "rank",
#         "rank_squares",
#         "bold_percentage",
#         "id_percentage",
#     ]
#     checkpoint_name = "checkpoints/models.pkl"
#
#     test_df, result = extract_test_features(file)
#
#     if isinstance(test_df, pd.DataFrame):
#         test_df = create_test_features(test_df)
#     else:
#         print(result)
#
#     _, target = inference_models(checkpoint_name, test_df, columns_to_use)
#
#     result = []
#     for page_layout in tqdm(extract_pages(file)):
#         texts = []
#         for element in page_layout:
#             if isinstance(element, LTTextContainer):
#                 texts.append(element.get_text().replace("\n", ""))
#         distances = calculate_distances(target, texts)
#
#         for window, distance in distances.items():
#             if distance < 20:
#                 result.append(window)

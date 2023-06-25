import re
import pickle
import warnings
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


def calculate_distances(target, list_of_strings):
    target_length = len(target.split())
    distances = {}

    for string in list_of_strings:
        string_words = string.split()

        # If the string has at least as many words as the target
        if len(string_words) >= target_length:
            for i in range(len(string_words) - target_length + 1):
                window = " ".join(string_words[i : i + target_length])
                distance = lev.distance(target, window)

                # Save the distance for this window
                distances[window] = (distance / len(target)) * 100
        else:
            # If the string has fewer words than the target
            distance = lev.distance(target, string)
            distances[string] = (distance / len(target)) * 100

    return distances


def replace_multiple_spaces(text):
    return re.sub(" +", " ", text)


def get_matches(file, target):
    result = []
    for i, page_layout in enumerate(tqdm(extract_pages(file))):
        _x1, _y1, _x2, _y2 = page_layout.bbox
        texts = []
        relative_coords = []
        for element in page_layout:
            if isinstance(element, LTTextContainer):
                # print(element.get_text())
                x1, y1, x2, y2 = element.bbox
                relative_coords.append(
                    [x1 / _x2, y1 / _y2, (x2 - x1) / _x2, (y2 - y1) / _y2]
                )

                texts.append(
                    replace_multiple_spaces(element.get_text().replace("\n", ""))
                )
        distances = calculate_distances(target, texts)

        for window, distance in distances.items():
            if distance / len(target) < 0.2:
                # print(i)
                # print(window)
                for j in range(len(texts)):
                    if window in texts[j]:
                        rel_coord = relative_coords[j]
                        break
                result.append(
                    {
                        "page": i + 1,
                        "window": window,
                        "coordinates": rel_coord,
                        "distance": distance / len(target),
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

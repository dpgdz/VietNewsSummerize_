import pandas as pd


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Xử lý dataframe chung cho mọi nguồn:
     - Drop duplicates theo 'link'
     - Fill NaN author = 'Unknown'
     - Drop NaN ở 'content' và 'date'
     - Parse datetime nếu cần, drop NaT
     - Chuẩn hóa 'source' & 'category'
    """
    df = df.drop_duplicates(subset='link', keep='first').copy()
    df['author'] = df.get('author', pd.Series()).fillna('Unknown')
    df = df.dropna(subset=['content', 'date'])

    if df['date'].dtype == object:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])

    df['source'] = df['source'].astype(str).str.strip().str.lower()
    df['category'] = df['category'].astype(str).str.strip()

    return df.reset_index(drop=True)
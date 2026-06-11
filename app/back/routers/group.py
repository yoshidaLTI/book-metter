import mimetypes
import shutil  # 不要になるが他で使っていれば残す
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session
from .. import database, crud, schemas, auth_utils ,models
from .. import dependencies
from fastapi import APIRouter, Depends, HTTPException, Query ,UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from .. import database, crud, schemas, auth_utils ,models
from .. import dependencies
import urllib.parse

import os
import uuid

router = APIRouter(prefix="/api/groups", tags=["groups"])

# 🚨 1. 危険なファイル（実行ファイル）のブラックリスト
DANGER_MAGIC_NUMBERS = {
    b'MZ': 'application/x-msdownload',       # Windowsの .exe / .dll
    b'\x7fELF': 'application/x-elf',         # Linuxの実行ファイル
    b'\xca\xfe\xba\xbe': 'application/x-mach-binary', # Macの実行ファイル
}

# 🟢 2. 中身を厳格にチェックしたいファイルのマジックナンバー
SAFE_MAGIC_NUMBERS = {
    b'\x89PNG\r\n\x1a\n': 'image/png',
    b'\xff\xd8\xff': 'image/jpeg',
    b'%PDF-': 'application/pdf',
}

# 📋 3. 読書メーターアプリで許可するファイル形式（ホワイトリスト）
# パワポやWordは「PDF統一」にしたため、これだけで全てのユースケースをカバー！
ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "text/plain",         # ソースコード貼り付け用のテキストファイル
    "application/pdf"     # 発表スライド、レポートなどの資料用PDF
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 5MB

@router.post("/", response_model=schemas.Group)
def create_group(
    group: schemas.GroupCreate,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """グループを新規作成する。ownerは自動でログイン中のユーザーになる。"""
    hashed = auth_utils.hash_password(group.password)
    return crud.create_group(db=db, group=group, hashed_password=hashed)


@router.get("/", response_model=list[schemas.Group])
def get_all_groups(
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """全グループを取得する（グループ検索画面用）。"""
    return crud.get_all_groups(db)



@router.get("/my-list", response_model=list[schemas.Group])
def get_my_groups(
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """ログイン中のユーザーが所属しているグループ一覧を取得する。"""
    return crud.get_user_groups(db, current_user_id)

# アクティビティ機能のAPI入口。
# フロントはこのURLを呼び出して、ホーム画面に「誰が・いつ・どのグループへ進捗を追加したか」を表示する。
@router.get("/activities", response_model=list[schemas.ProgressActivity])
def get_my_progress_activities(
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    return crud.get_user_progress_activities(db, current_user_id)

@router.get("/search/by-name", response_model=list[schemas.Group])
def search_by_name(
    q: str = Query(..., description="グループ名の検索キーワード"),
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """グループ名で検索する。"""
    results = crud.search_groups_by_name(db, q)
    if not results:
        raise HTTPException(status_code=404, detail="該当するグループが見つかりません")
    return results


@router.get("/search/by-book", response_model=list[schemas.Group])
def search_by_book(
    q: str = Query(..., description="本のタイトルの検索キーワード"),
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """課題図書のタイトルで検索する。"""
    results = crud.search_groups_by_book(db, q)
    if not results:
        raise HTTPException(status_code=404, detail="該当するグループが見つかりません")
    return results


@router.delete("/{group_id}")
def delete_group(
    group_id: int,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """グループを削除する。オーナーのみ可能。"""
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")
    if group.owner != current_user_id:
        raise HTTPException(status_code=403, detail="オーナーのみ削除できます")
    crud.delete_group(db, group_id)
    return {"message": "グループを削除しました"}

@router.patch("/{group_id}", response_model=schemas.Group)
def update_group(
    group_id: int,
    update_data: schemas.GroupUpdate,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """グループ設定を更新する。オーナーのみ可能。"""
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")
    if group.owner != current_user_id:
        raise HTTPException(status_code=403, detail="オーナーのみ設定を変更できます")
    
    hashed = auth_utils.hash_password(update_data.password) if update_data.password else None
    updated = crud.update_group(db, group_id, update_data, hashed)
    return updated


@router.get("/{group_id}", response_model=schemas.Group)
def get_group(
    group_id: int,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """指定したグループの詳細を取得する。"""
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")
    if not crud.is_group_member(db, group_id, current_user_id):
        raise HTTPException(status_code=403, detail="グループメンバーのみ閲覧できます")
    return group

@router.post("/{group_id}/join")
def join_group(
    group_id: int,
    password: str = Query(None),
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """グループに参加する。is_lock=true の場合は password が必要。"""
    success, message = crud.join_group(db, group_id, current_user_id, password)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@router.post("/{group_id}/leave")
def leave_group(
    group_id: int,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """グループから退会する。オーナーは退会不可。"""
    success, message = crud.leave_group(db, group_id, current_user_id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}


@router.post("/{group_id}/progress", response_model=schemas.Progress)
def create_progress(
    group_id: int,
    progress: schemas.ProgressCreate,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """進捗を記録する。"""
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")
    return crud.create_progress(db, progress, group_id, current_user_id)


@router.get("/{group_id}/progress", response_model=list[schemas.Progress])
def get_progresses(
    group_id: int,
    limit: int = Query(None),  
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")
    return crud.get_group_progresses(db, group_id, limit=limit)


@router.patch("/{group_id}/progress/{progress_id}", response_model=schemas.Progress)
def update_progress(
    group_id: int,
    progress_id: int,
    update_data: schemas.ProgressUpdate,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """進捗を編集する。自分の進捗またはオーナーのみ可能。"""
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")

    progress = db.query(models.Progress).filter(models.Progress.id == progress_id).first()
    if not progress:
        raise HTTPException(status_code=404, detail="進捗が見つかりません")

    if progress.user_id != current_user_id and group.owner != current_user_id:
        raise HTTPException(status_code=403, detail="編集権限がありません")

    return crud.update_progress(db, progress_id, update_data)


@router.delete("/{group_id}/progress/{progress_id}")
def delete_progress(
    group_id: int,
    progress_id: int,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """進捗を削除する。自分の進捗またはオーナーのみ可能。"""
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")

    progress = db.query(models.Progress).filter(models.Progress.id == progress_id).first()
    if not progress:
        raise HTTPException(status_code=404, detail="進捗が見つかりません")

    if progress.user_id != current_user_id and group.owner != current_user_id:
        raise HTTPException(status_code=403, detail="削除権限がありません")

    crud.delete_progress(db, progress_id)
    return {"message": "削除しました"}

#~=================================================================
#　ファイルアップロードのためのエンドポイント
#~=================================================================
UPLOAD_DIR = "/app/back/uploads"

@router.post("/{group_id}/progress/{progress_id}/upload", response_model=schemas.Progress)
async def upload_progress_file(
    group_id: int,
    progress_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    # ステップ0：申告サイズの事前足切り
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="ファイルサイズが上限（10MB）を超えています。")

    # ステップ1：先頭8バイトでマジックナンバー取得
    header = await file.read(8)
    await file.seek(0)

    # ステップ2：チャンク読み込みで実サイズ確認（メモリ安全）
    actual_size = 0
    chunks = []
    while True:
        chunk = await file.read(65536)  # 64KBずつ読む
        if not chunk:
         break
        actual_size += len(chunk)
        if actual_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="ファイルサイズが上限（5MB）を超えています。")
        chunks.append(chunk)
    await file.seek(0)

    # ステップ3：実行ファイル偽装チェック
    for danger_magic in DANGER_MAGIC_NUMBERS.keys():
        if header.startswith(danger_magic):
            raise HTTPException(status_code=400, detail="不正なファイル形式です。実行ファイルはアップロードできません。")

    # ステップ4：MIMEタイプ判定
    mime_type = None
    for magic, mime in SAFE_MAGIC_NUMBERS.items():
        if header.startswith(magic):
            mime_type = mime
            break
    if not mime_type:
        mime_type, _ = mimetypes.guess_type(file.filename)
        if not mime_type:
            mime_type = file.content_type or "application/octet-stream"

    # ステップ5：ホワイトリストチェック
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"許可されていない形式です ({mime_type})。画像(PNG/JPEG)、テキスト(.txt)、資料(PDF)のみアップロード可能です。"
        )

    # ステップ6：保存
    filename = f"{uuid.uuid4()}_{file.filename}"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_location = os.path.join(UPLOAD_DIR, filename)

    with open(file_location, "wb") as f:
        f.write(b"".join(chunks))

    # ステップ7：所有者確認してDB更新
    progress = db.query(models.Progress).filter(
        models.Progress.id == progress_id,
        models.Progress.group_id == group_id,
        models.Progress.user_id == current_user_id
    ).first()
    if not progress:
        raise HTTPException(status_code=404, detail="指定された進捗データが見つかりません。")

    progress.url = f"/uploads/{filename}"
    progress.file_type = mime_type
    db.commit()
    db.refresh(progress)

    return progress


#~=================================================================
#　ファイルダウンロードのためのエンドポイント
#~=================================================================
@router.get("/{group_id}/progress/{progress_id}/download")
async def download_progress_file(
    group_id: int,
    progress_id: int,
    db: Session = Depends(database.get_db),
    current_user_id: int = Depends(dependencies.get_current_user_id)
):
    """進捗に添付されたファイルをダウンロードする。グループメンバーであれば誰でも可能。"""
    # 1. グループの存在チェック
    group = crud.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="グループが見つかりません")

    # 2. 進捗の存在チェック
    progress = db.query(models.Progress).filter(models.Progress.id == progress_id).first()
    if not progress:
        raise HTTPException(status_code=404, detail="進捗が見つかりません")
    
    # 3. グループメンバーかチェック（セキュリティ）
    if not crud.is_group_member(db, group_id, current_user_id):
        raise HTTPException(status_code=403, detail="グループメンバーのみダウンロードできます")

    # 4. ファイルが添付されているかチェック
    if not progress.url:
        raise HTTPException(status_code=404, detail="この進捗にファイルは添付されていません")

    # 5. 実ファイルパスの組み立てと存在確認（ディレクトリトラバーサル対策）
    # progress.url からファイル名部分（uuid.ext）のみを安全に抽出
    filename = os.path.basename(progress.url)
    filepath = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="ファイルがサーバー上に見つかりません")

    # 6. 元のファイル名がDB等に保存されていない場合の対策
    # 本来はアップロード時の元のファイル名（例: 報告書.pdf）をDBに保存しておくのが理想です。
    # 保持していない場合は、仮のファイル名を生成してブラウザにダウンロードさせます。
    download_name = f"download_{progress_id}{os.path.splitext(filename)[1]}"
    
    # 日本語のファイル名でも文字化けしないようにURLエンコード処理
    # 例: "報告書.pdf" -> "utf-8''%E5%A0%B1%E5%91%8A%E6%9B%B8.pdf"
    encoded_filename = urllib.parse.quote(download_name)
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
    }

    # 7. FastAPIのFileResponseを使い、ストリーミングで安全に返却
    return FileResponse(
        path=filepath,
        media_type=progress.file_type or "application/octet-stream",
        headers=headers
    )

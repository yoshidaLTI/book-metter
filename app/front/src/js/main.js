// app/front/src/js/main.js
// 現在のログインユーザー情報を保持する変数
let currentUserId = null;

/**
 * 認証チェック
 */
async function checkAuthAndLoad() {
    try {
        const user = await getCurrentUser();
        currentUserId = user.id;
        // 成功した時だけ本を読み込む（これが正解のフロー）
        await fetchBooks(); 
    } catch (error) {
        console.warn("未認証のためログイン画面へ遷移します:", error);
        
        // 【テスト用】もしこれが表示されれば、リダイレクト処理までは到達しています
        // alert("ログインが必要です。ログイン画面へ移動します。");

        // 実際のパスが /public/login.html か /login.html かをブラウザで確認してください
        window.location.href = "/public/login.html";
    }
}

/**
 * ユーザープロフィールの読み込みと表示
 */
document.addEventListener('DOMContentLoaded', async () => {
    await loadUserProfile();
});
// ログイン中のユーザー情報を取得して画面に反映する関数
async function loadUserProfile() {
    try {
        // Cookieを自動で送信して、自分の情報を取得する
        const response = await fetch('/api/auth/me');
        
        if (!response.ok) {
            // セッションが切れているか、未ログインならログイン画面へ弾く（門番の役割）
            window.location.href = "/login.html";
            return;
        }

        const user = await response.json();
        
        // 取得した情報をHTMLにセットする！
        document.getElementById('user-id').innerText = user.id;
        document.getElementById('user-name').innerText = user.username;
        
    } catch (error) {
        console.error("ユーザー情報の取得に失敗しました", error);
    }
}


/**
 * ログアウト
 */
async function logout() {
    if (!confirm("ログアウトしますか？")) return;

    try {
        await postLogout();
        // 成功したらログイン画面へ飛ばす
        // ※ 先ほど成功した正しいパス（/public/login.html か /login.html）に合わせてください
        window.location.href = "/public/login.html"; 
    } catch (error) {
        alert(error.message);
    }
}



/**
 * 本の一覧取得と表示
 */
async function fetchBooks() {
    const bookListDiv = document.getElementById('book-list');
    
    // 画面上の隠し要素(innerText)から取るのではなく、変数から使うのが安全
    if (!currentUserId) return;

    try {
        const books = await getBooks(currentUserId);
        
        // データが空の場合のケア
        if (books.length === 0) {
            bookListDiv.innerHTML = "<p style='text-align:center; color:#666;'>登録されている本がありません。</p>";
            return;
        }

        bookListDiv.innerHTML = books.map(book => {
            // --- プログレスバーの生成 ---
            let progressBarHtml = `
                <div class="progress-container" style="background: #eee; height: 12px; border-radius: 6px; margin: 15px 0; position: relative; overflow: hidden; border: 1px solid #ddd;">
            `;

            if (book.progress_logs && book.progress_logs.length > 0) {
                book.progress_logs.forEach(log => {
                    const left = ((log.start_page - 1) / book.total_pages) * 100;
                    const width = ((log.end_page - log.start_page + 1) / book.total_pages) * 100;
                    
                    progressBarHtml += `
                        <div style="
                            position: absolute; 
                            left: ${left}%; 
                            width: ${width}%; 
                            background: #2ecc71; 
                            height: 100%;
                            opacity: 0.6;
                            border-right: 1px solid #27ae60;
                        " title="${log.start_page}〜${log.end_page}ページ"></div>
                    `;
                });
            }
            progressBarHtml += `</div>`;

            return `
                <div class="book-card" style="border: 1px solid #ccc; margin: 20px 0; padding: 20px; border-radius: 10px; background: white; position: relative; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <button onclick="requestDeleteBook(${book.id}, '${book.title}')" style="position: absolute; top: 10px; right: 10px; background:#ff4757; color:white; border:none; border-radius:4px; padding: 5px 10px; cursor:pointer; font-size:12px;">削除</button>
                    
                    <h3>📖 ${book.title}</h3>
                    <p>進捗: <strong>${book.total_read_pages}</strong> / ${book.total_pages} ページ (${Math.round((book.total_read_pages/book.total_pages)*100)}%)</p>
                    
                    ${progressBarHtml}

                    <div style="background: #f9f9f9; padding: 15px; border-radius: 5px; margin-top: 10px; border: 1px dashed #4a90e2;">
                        <h4 style="margin: 0 0 10px 0; font-size: 14px; color: #4a90e2;">進捗を記録する</h4>
                        <div style="display: flex; gap: 5px; flex-wrap: wrap;">
                            <input type="date" id="date-${book.id}" value="${new Date().toISOString().split('T')[0]}" style="padding:5px;">
                            <input type="number" id="start-${book.id}" placeholder="開始" style="width: 60px; padding:5px;"> 〜 
                            <input type="number" id="end-${book.id}" placeholder="終了" style="width: 60px; padding:5px;">
                            <input type="text" id="memo-${book.id}" placeholder="一言メモ" style="flex-grow: 1; min-width: 100px; padding:5px;">
                            <button onclick="submitProgress(${book.id})" style="background: #4a90e2; color: white; border: none; padding: 5px 15px; border-radius: 4px; cursor: pointer;">記録</button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error("Fetch books error:", error);
        bookListDiv.innerHTML = "<p>データの取得に失敗しました。ログインし直してください。</p>";
    }
}


async function submitProgress(bookId) {
    // 入力値の取得
    const dateInput = document.getElementById(`date-${bookId}`).value;
    const startInput = document.getElementById(`start-${bookId}`).value;
    const endInput = document.getElementById(`end-${bookId}`).value;
    const memo = document.getElementById(`memo-${bookId}`).value;

    // 1. 数値変換（空文字や文字列を弾く）
    // Number.isInteger を使うことで「整数のみ」を許可し、小数を弾きます
    const startPage = Number(startInput);
    const endPage = Number(endInput);

    // --- チェック開始 ---

    // A. 必須項目チェック
    if (!dateInput || startInput === "" || endInput === "") {
        alert("日付、開始ページ、終了ページをすべて入力してください。");
        return;
    }

    // B. 整数チェック & マイナス値チェック
    if (!Number.isInteger(startPage) || !Number.isInteger(endPage)) {
        alert("ページ数は整数で入力してください。");
        return;
    }
    if (startPage < 1 || endPage < 1) {
        alert("ページ数にマイナスの値や0は入力できません。");
        return;
    }

    // C. 範囲の整合性チェック (10〜1 などの逆転を防止)
    if (startPage > endPage) {
        alert("開始ページは終了ページ以下の数字にしてください。");
        return;
    }

    // D. 本の最大ページ数を超えていないかチェック
    // DOMから現在の本の最大ページ数を取得
    try {
        const books = await getBooks(currentUserId);
        const currentBook = books.find(b => b.id === bookId);
        
        if (currentBook && endPage > currentBook.total_pages) {
            alert(`この本は最大 ${currentBook.total_pages} ページです。それを超える値は入力できません。`);
            return;
        }
    } catch (e) {
        console.error("バリデーション中のデータ取得に失敗", e);
    }

    // --- すべてのチェックを通過したら送信 ---
    const data = {
        date: dateInput,
        start_page: startPage,
        end_page: endPage,
        memo: memo
    };

    try {
        await postProgress(bookId, data);
        alert("記録しました！");
        fetchBooks();
    } catch (error) {
        alert("エラー: " + error.message);
    }
}

async function submitNewBook() {
    const userId = currentUserId;
    const data = {
        title: document.getElementById('book-title').value,
        total_pages: parseInt(document.getElementById('book-pages').value),
        target_date: document.getElementById('book-target').value,
        user_id: userId
    };

    if (!data.title || isNaN(data.total_pages) || !data.target_date) {
        alert("すべての項目を入力してください");
        return;
    }

    try {
        await postBook(data);
        alert("本を登録しました！");
        // 入力欄をクリア
        document.getElementById('book-title').value = "";
        document.getElementById('book-pages').value = "";
        document.getElementById('book-target').value = "";
        // 一覧を再読み込み
        fetchBooks();
    } catch (error) {
        alert(error.message);
    }
}

async function requestDeleteBook(bookId, title) {
    if (!confirm(`本「${title}」を削除してもよろしいですか？\n※関連する進捗データもすべて消去されます。`)) {
        return;
    }

    try {
        await deleteBook(bookId);
        alert("削除しました");
        fetchBooks(); // リストを更新
    } catch (error) {
        alert(error.message);
    }
}


// ページ読み込み時に自動実行
window.onload = async () => {
    await checkAuthAndLoad();// まず認証チェック
};
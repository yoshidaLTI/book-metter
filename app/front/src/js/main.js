// app/front/src/js/main.js
let currentUser = null;

// ========================
// 初期化
// ========================
window.onload = async () => {
    await checkAuthAndLoad();
};

async function checkAuthAndLoad() {
    try {
        const res = await fetch('/api/auth/me');
        if (!res.ok) throw new Error("Unauthorized");
        currentUser = await res.json();

        const el = document.getElementById('header-username');
        if (el) el.innerText = currentUser.username;

        // ページ別初期化
        if (document.getElementById('group-list'))   await loadMyGroups();
        if (document.getElementById('search-results') &&
            document.getElementById('search-input'))  initSearchBookPage();
        if (document.getElementById('bookshelf-list')) await loadBookshelf();
        if (document.getElementById('group-search-results')) {} 
        if (document.getElementById('group-detail-main')) await loadGroupDetail();
        if (document.getElementById('group-setting-main')) await loadGroupSetting();

    } catch (e) {
        console.warn("未認証:", e);
        window.location.href = "/public/login.html";
    }
}

// ========================
// ログアウト（共通）
// ========================
async function logout() {
    if (!confirm("ログアウトしますか？")) return;
    try {
        await postLogout();
        window.location.href = "/public/login.html";
    } catch (e) {
        alert(e.message);
    }
}

// ========================
// ユーティリティ（共通）
// ========================
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function calculateTotalRead(progresses) {
    if (!progresses.length) return 0;
    const intervals = progresses
        .map(p => [p.start_page, p.end_page])
        .sort((a, b) => a[0] - b[0]);
    const merged = [];
    for (const [s, e] of intervals) {
        if (!merged.length || s > merged[merged.length - 1][1] + 1) {
            merged.push([s, e]);
        } else {
            merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], e);
        }
    }
    return merged.reduce((sum, [s, e]) => sum + (e - s + 1), 0);
}

// ========================================
// index.html: 参加中グループ一覧
// ========================================
async function loadMyGroups() {
    const container = document.getElementById('group-list');
    try {
        const groups = await getMyGroups();

        if (groups.length === 0) {
            container.innerHTML = `
                <div style="grid-column:1/-1; text-align:center; padding:60px 20px; color:#999;">
                    <p style="font-size:3rem; margin-bottom:10px;">📚</p>
                    <p style="font-size:1.1rem; margin-bottom:20px;">まだグループに参加していません</p>
                    <a href="/public/search-group.html" class="add-btn-small">グループを探す</a>
                </div>`;
            return;
        }

        const groupsWithProgress = await Promise.all(
            groups.map(async (g) => {
                try {
                    const progresses = await getGroupProgresses(g.id, 20);
                    return { ...g, progresses };
                } catch {
                    return { ...g, progresses: [] };
                }
            })
        );

        // 最新の進捗idが大きい順にソート（進捗がないグループは末尾）
        groupsWithProgress.sort((a, b) => {
            const latestA = a.progresses.length > 0 ? a.progresses[0].id : -1;
            const latestB = b.progresses.length > 0 ? b.progresses[0].id : -1;
            return latestB - latestA;
        });

        const displayGroups = groupsWithProgress.slice(0, 20);
        container.innerHTML = displayGroups.map(renderGroupCard).join('');
        if (groupsWithProgress.length > 20) {
            container.innerHTML += `
                <div style="grid-column:1/-1; text-align:right; padding-top:10px;">
                    <a href="/public/bookshelf.html" style="font-weight:bold;">もっと見る →</a>
                </div>`;
        }

    } catch (e) {
        container.innerHTML = `<p style="color:red; grid-column:1/-1;">グループの取得に失敗しました</p>`;
        console.error(e);
    }
}

function renderGroupCard(group) {
    const totalPages = group.total_pages || 0;
    const myProgresses = (group.progresses || []).filter(p => p.user_id === currentUser.id);
    const totalRead = calculateTotalRead(myProgresses);
    const percent = totalPages > 0 ? Math.min(100, Math.round((totalRead / totalPages) * 100)) : 0;

    const segments = myProgresses.map(p => {
        const left  = totalPages > 0 ? ((p.start_page - 1) / totalPages) * 100 : 0;
        const width = totalPages > 0 ? ((p.end_page - p.start_page + 1) / totalPages) * 100 : 0;
        return `<div class="range-segment" style="left:${left}%; width:${width}%;"></div>`;
    }).join('');

    const bookInfo = group.title
        ? `<div style="display:flex; gap:10px; align-items:flex-start; margin-bottom:12px;">
            ${group.small_cover_url
                ? `<img src="${group.small_cover_url}" alt="書影" style="width:45px; height:63px; object-fit:cover; border-radius:3px; flex-shrink:0;">`
                : `<div style="width:45px; height:63px; background:#eee; border-radius:3px; flex-shrink:0;"></div>`}
            <div>
                <div style="font-weight:bold; font-size:0.95rem;">${escapeHtml(group.title)}</div>
                ${group.author ? `<div style="font-size:0.8rem; color:#999; margin-top:3px;">${escapeHtml(group.author)}</div>` : ''}
                <div style="font-size:0.8rem; color:#999; margin-top:2px;">${totalPages} ページ</div>
            </div>
           </div>`
        : `<p style="color:#999; font-size:0.9rem; margin-bottom:12px;">課題図書未設定</p>`;

    const lockBadge = group.is_lock
        ? `<span style="font-size:0.75rem; background:#fff3cd; color:#856404; padding:2px 7px; border-radius:10px; border:1px solid #ffc107;">🔒 鍵あり</span>`
        : `<span style="font-size:0.75rem; background:#d4edda; color:#155724; padding:2px 7px; border-radius:10px; border:1px solid #28a745;">🔓 公開</span>`;

    return `
        <div class="group-card" style="flex-direction:column;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
                <h3 class="group-name" style="margin:0; font-size:1.05rem;">
                    <a href="/public/group-detail.html?id=${group.id}">${escapeHtml(group.name)}</a>
                </h3>
                ${lockBadge}
            </div>
            ${bookInfo}
            <div class="progress-container" style="margin-bottom:12px;">
                <span class="progress-text">自分の進捗: ${totalRead} / ${totalPages} P (${percent}%)</span>
                <div class="range-bar-wrapper">${segments}</div>
            </div>
            <div class="record-area">
                <div class="progress-input-group">
                    <input type="number" id="start-${group.id}" placeholder="開始" min="1" max="${totalPages}">
                    <span>〜</span>
                    <input type="number" id="end-${group.id}" placeholder="終了" min="1" max="${totalPages}">
                    <span>ページ</span>
                </div>
                <div class="memo-input-group">
                    <input type="text" id="memo-${group.id}" placeholder="メモ（任意）">
                    <button class="btn-record" onclick="submitProgress(${group.id}, ${totalPages})">記録</button>
                </div>
            </div>
        </div>`;
}

async function submitProgress(groupId, totalPages) {
    const startInput = document.getElementById(`start-${groupId}`).value;
    const endInput   = document.getElementById(`end-${groupId}`).value;
    const memo       = document.getElementById(`memo-${groupId}`).value;
    const startPage  = Number(startInput);
    const endPage    = Number(endInput);

    if (!startInput || !endInput)                          { alert("開始・終了ページを入力してください"); return; }
    if (!Number.isInteger(startPage) || !Number.isInteger(endPage)) { alert("ページ数は整数で入力してください"); return; }
    if (startPage < 1 || endPage < 1)                     { alert("1以上のページ数を入力してください"); return; }
    if (startPage > endPage)                               { alert("開始ページは終了ページ以下にしてください"); return; }
    if (totalPages > 0 && endPage > totalPages)            { alert(`この本は最大 ${totalPages} ページです`); return; }

    try {
        await postGroupProgress(groupId, { start_page: startPage, end_page: endPage, memo });
        alert("記録しました！");
        // ページによって呼び分ける
        if (document.getElementById('group-list')) {
            await loadMyGroups();
        } else if (document.getElementById('bookshelf-list')) {
            await loadBookshelf();
        }
    } catch (e) {
        alert("エラー: " + e.message);
    }
}

// ========================================
// search-book.html: 本検索 & グループ作成
// ========================================
let selectedBook = null;

function initSearchBookPage() {
    // Enterキーで検索
    document.getElementById('search-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') runBookSearch();
    });
}

async function runBookSearch() {
    const q = document.getElementById('search-input').value.trim();
    if (!q) { alert("検索キーワードを入力してください"); return; }

    
    const type = document.getElementById('search-type').value;
    const container = document.getElementById('search-results');
    container.innerHTML = `<p style="text-align:center; color:#999; padding:30px;">検索中...</p>`;

    try {
        const results = type === 'title'
            ? await searchGoogleBooksByTitle(q)
            : await searchGoogleBooksByAuthor(q);

        if (!results || results.length === 0) {
            container.innerHTML = `<p style="text-align:center; color:#999; padding:30px;">該当する本が見つかりませんでした</p>`;
            return;
        }
        container.innerHTML = `<div class="book-list">${results.map(renderBookResult).join('')}</div>`;

    } catch (e) {
        container.innerHTML = `<p style="color:red; text-align:center; padding:30px;">検索に失敗しました: ${e.message}</p>`;
    }
}

function renderBookResult(book) {
    const cover = book.small_cover_url
        ? `<img src="${book.small_cover_url}" alt="書影" class="book-cover">`
        : `<div class="book-cover" style="background:#eee; display:flex; align-items:center; justify-content:center; color:#bbb; font-size:2rem;">📖</div>`;

    const bookJson = escapeHtml(JSON.stringify(book));

    return `
        <div class="book-card">
            ${cover}
            <div class="book-info">
                <div>
                    <h3 class="book-title" style="white-space:normal; overflow:hidden; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;">${escapeHtml(book.title || '(タイトル不明)')}</h3>
                    <div class="book-meta">
                        ${book.author    ? `<span class="book-author">${escapeHtml(book.author)}</span>` : ''}
                        ${book.publisher ? `<span class="book-publisher">${escapeHtml(book.publisher)}</span>` : ''}
                    </div>
                    ${book.description ? `<p style="font-size:0.85rem; color:#666; margin:8px 0 0;
                        display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;">
                        ${escapeHtml(book.description)}</p>` : ''}
                </div>
                <div class="card-actions">
                    <button class="btn-record" onclick='openCreateModal(${bookJson})'>このグループを作成する</button>
                </div>
            </div>
        </div>`;
}

function openCreateModal(book) {
    selectedBook = book;
    document.getElementById('modal-book-title').innerText  = book.title || '(タイトル不明)';
    document.getElementById('modal-book-author').innerText = book.author || '';
    const coverEl = document.getElementById('modal-book-cover');
    coverEl.src = book.small_cover_url || '';
    coverEl.style.display = book.small_cover_url ? 'block' : 'none';

    document.getElementById('modal-total-pages').value = '';
    document.getElementById('modal-group-name').value  = book.title ? `${book.title}読書会` : '';
    document.getElementById('modal-is-lock').checked   = false;
    document.getElementById('modal-password').value    = '';
    document.getElementById('password-field').style.display = 'none';
    document.getElementById('create-modal').style.display   = 'flex';
}

function openCreateBookModal() {
    document.getElementById('modal-book-title').innerText  = '';
    document.getElementById('modal-book-author').innerText = '';
    const coverEl = document.getElementById('modal-book-cover');
    coverEl.src = '';
    coverEl.style.display = 'none';

    document.getElementById('modal-total-pages').value = '';
    document.getElementById('modal-group-name').value  = '';
    document.getElementById('modal-is-lock').checked   = false;
    document.getElementById('modal-password').value    = '';
    document.getElementById('password-field').style.display = 'none';
    document.getElementById('create-book-modal').style.display   = 'flex';

}    

function closeCreateModal() {
    document.getElementById('create-modal').style.display = 'none';
    selectedBook = null;
}

function closeCreateBookModal() {
    document.getElementById('create-book-modal').style.display = 'none';
    selectedBook = null;
}

function togglePasswordField() {
    const isLock = document.getElementById('modal-is-lock').checked;
    document.getElementById('password-field').style.display = isLock ? 'block' : 'none';
}


function toggleBookPasswordField() {
    const isLock = document.getElementById('modal-book-is-lock').checked;
    document.getElementById('book-password-field').style.display = isLock ? 'block' : 'none';
}

async function submitCreateGroup() {
    if (!selectedBook || !currentUser) return;

    const totalPages = parseInt(document.getElementById('modal-total-pages').value);
    const groupName  = document.getElementById('modal-group-name').value.trim();
    const isLock     = document.getElementById('modal-is-lock').checked;
    const password   = document.getElementById('modal-password').value;

    if (!totalPages || totalPages < 1) { alert("総ページ数を入力してください"); return; }
    if (!groupName)                    { alert("グループ名を入力してください"); return; }
    if (isLock && !password)           { alert("パスワードを入力してください"); return; }

    const data = {
        name:          groupName,
        owner:         currentUser.id,
        is_lock:       isLock,
        password:      password || "none",
        title:         selectedBook.title         || null,
        total_pages:   totalPages,
        author:        selectedBook.author        || null,
        publisher:     selectedBook.publisher     || null,
        published_date:selectedBook.published_date|| null,
        description:   selectedBook.description   || null,
        self_link:     selectedBook.self_link      || null,
        api_id:        selectedBook.api_id         || null,
        api_etag:      selectedBook.api_etag       || null,
        small_cover_url:selectedBook.small_cover_url|| null,
        cover_url:     selectedBook.cover_url      || null,
    };

    try {
        const group = await postCreateGroup(data);
        alert(`グループ「${group.name}」を作成しました！`);
        closeCreateModal();
        window.location.href = `/public/group-detail.html?id=${group.id}`;
    } catch (e) {
        alert("エラー: " + e.message);
    }
}

async function submitCreateBookGroup() {

    const title = document.getElementById('modal-book-title-input').value.trim();
    const author = document.getElementById('modal-book-author-input').value.trim();

    const totalPages = parseInt(document.getElementById('modal-book-total-pages').value);
    const groupName  = document.getElementById('modal-book-group-name').value.trim();
    const isLock     = document.getElementById('modal-book-is-lock').checked;
    const password   = document.getElementById('modal-book-password').value;

    if (!title) { alert("タイトルを入力してください"); return; }
    if (!totalPages || totalPages < 1) { alert("総ページ数を入力してください"); return; }
    if (!groupName)                    { alert("グループ名を入力してください"); return; }
    if (isLock && !password)           { alert("パスワードを入力してください"); return; }

    const data = {
        name:          groupName,
        owner:         currentUser.id,
        is_lock:       isLock,
        password:      password || "none",
        title:         title         || null,
        total_pages:   totalPages,
        author:        author        || null,
        publisher:   null,
        published_date: null,
        description:    null,
        self_link:      null,
        api_id:         null,
        api_etag:       null,
        small_cover_url: null,
        cover_url:      null,
    };

    try {
        const group = await postCreateGroup(data);
        alert(`グループ「${group.name}」を作成しました！`);
        closeCreateBookModal();
        window.location.href = `/public/group-detail.html?id=${group.id}`;
    } catch (e) {
        alert("エラー: " + e.message);
    }
}

// ========================================
// bookshelf.html: 自分の本棚
// ========================================
let allMyGroups = []; // フィルタ用にキャッシュ

async function loadBookshelf() {
    const container = document.getElementById('bookshelf-list');
    try {
        const groups = await getMyGroups();

        if (groups.length === 0) {
            container.innerHTML = `
                <div style="grid-column:1/-1; text-align:center; padding:60px 20px; color:#999;">
                    <p style="font-size:3rem; margin-bottom:10px;">📚</p>
                    <p style="font-size:1.1rem; margin-bottom:20px;">まだグループに参加していません</p>
                    <a href="/public/search-group.html" class="add-btn-small">グループを探す</a>
                </div>`;
            return;
        }

        const groupsWithProgress = await Promise.all(
            groups.map(async (g) => {
                try {
                    const progresses = await getGroupProgresses(g.id);
                    return { ...g, progresses };
                } catch {
                    return { ...g, progresses: [] };
                }
            })
        );

        // 最新の進捗id順にソート
        groupsWithProgress.sort((a, b) => {
            const latestA = a.progresses.length > 0 ? a.progresses[0].id : -1;
            const latestB = b.progresses.length > 0 ? b.progresses[0].id : -1;
            return latestB - latestA;
        });

        allMyGroups = groupsWithProgress;
        renderBookshelf(allMyGroups);

    } catch (e) {
        container.innerHTML = `<p style="color:red; grid-column:1/-1;">グループの取得に失敗しました</p>`;
        console.error(e);
    }
}

function renderBookshelf(groups) {
    const container = document.getElementById('bookshelf-list');
    if (groups.length === 0) {
        container.innerHTML = `<p style="color:#999; text-align:center; grid-column:1/-1;">該当するグループが見つかりませんでした</p>`;
        return;
    }
    container.innerHTML = groups.map(renderGroupCard).join('');
}

function filterBookshelf() {
    const q = document.getElementById('bookshelf-search-input').value.trim().toLowerCase();
    if (!q) {
        renderBookshelf(allMyGroups);
        return;
    }
    const filtered = allMyGroups.filter(g =>
        (g.name && g.name.toLowerCase().includes(q)) ||
        (g.title && g.title.toLowerCase().includes(q))
    );
    renderBookshelf(filtered);
}


// ========================================
// search-group.html: グループ検索
// ========================================
let joinTargetGroupId = null;

async function runGroupSearch() {
    const q = document.getElementById('group-search-input').value.trim();
    if (!q) { alert("キーワードを入力してください"); return; }

    const type = document.getElementById('search-type').value;
    const container = document.getElementById('group-search-results');
    container.innerHTML = `<p style="text-align:center; color:#999; grid-column:1/-1; padding:30px;">検索中...</p>`;

    try {
        const results = type === 'name'
            ? await searchGroupsByName(q)
            : await searchGroupsByBook(q);

        if (!results || results.length === 0) {
            container.innerHTML = `<p style="text-align:center; color:#999; grid-column:1/-1; padding:30px;">該当するグループが見つかりませんでした</p>`;
            return;
        }

        // 自分が参加済みのグループIDを取得
        const myGroups = await getMyGroups();
        const myGroupIds = new Set(myGroups.map(g => g.id));

        container.innerHTML = results.map(g => renderGroupSearchCard(g, myGroupIds)).join('');

    } catch (e) {
        container.innerHTML = `<p style="color:red; text-align:center; grid-column:1/-1; padding:30px;">検索に失敗しました: ${e.message}</p>`;
    }
}

function renderGroupSearchCard(group, myGroupIds) {
    const isJoined = myGroupIds.has(group.id);
    const totalPages = group.total_pages || 0;

    const bookInfo = group.title
        ? `<div style="display:flex; gap:10px; align-items:flex-start; margin-bottom:12px;">
            ${group.small_cover_url
                ? `<img src="${group.small_cover_url}" alt="書影" style="width:45px; height:63px; object-fit:cover; border-radius:3px; flex-shrink:0;">`
                : `<div style="width:45px; height:63px; background:#eee; border-radius:3px; flex-shrink:0;"></div>`}
            <div>
                <div style="font-weight:bold; font-size:0.95rem;">${escapeHtml(group.title)}</div>
                ${group.author ? `<div style="font-size:0.8rem; color:#999; margin-top:3px;">${escapeHtml(group.author)}</div>` : ''}
                <div style="font-size:0.8rem; color:#999; margin-top:2px;">${totalPages} ページ</div>
            </div>
           </div>`
        : '';

    const lockBadge = group.is_lock
        ? `<span style="font-size:0.75rem; background:#fff3cd; color:#856404; padding:2px 7px; border-radius:10px; border:1px solid #ffc107;">🔒 鍵あり</span>`
        : `<span style="font-size:0.75rem; background:#d4edda; color:#155724; padding:2px 7px; border-radius:10px; border:1px solid #28a745;">🔓 公開</span>`;

    const memberCount = group.members ? group.members.length : 0;

    // 参加済みバッジ・ボタン
    const actionArea = isJoined
        ? `<div style="display:flex; justify-content:space-between; align-items:center; margin-top:auto; padding-top:10px;">
            <span style="font-size:0.8rem; background:#e3f2fd; color:#1565c0; padding:4px 10px; border-radius:10px; border:1px solid #90caf9;">✅ 参加済み</span>
            <a href="/public/group-detail.html?id=${group.id}" class="btn-record" style="padding:6px 14px; font-size:0.85rem;">詳細を見る</a>
           </div>`
        : `<div style="text-align:right; margin-top:auto; padding-top:10px;">
            <button class="btn-record" style="padding:6px 14px; font-size:0.85rem;"
                onclick="handleJoinGroup(${group.id}, ${group.is_lock}, '${escapeHtml(group.name)}')">参加する</button>
           </div>`;

    return `
        <div class="group-card" style="flex-direction:column; ${isJoined ? 'opacity:0.75;' : ''}">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
                <h3 class="group-name" style="margin:0; font-size:1.05rem;">
                    ${escapeHtml(group.name)}
                </h3>
                ${lockBadge}
            </div>
            ${bookInfo}
            <div style="font-size:0.8rem; color:#999; margin-bottom:8px;">👥 ${memberCount}人参加中</div>
            ${actionArea}
        </div>`;
}

function handleJoinGroup(groupId, isLock, groupName) {
    if (isLock) {
        joinTargetGroupId = groupId;
        document.getElementById('join-modal-title').innerText = `「${groupName}」に参加する`;
        document.getElementById('join-password').value = '';
        document.getElementById('join-modal').style.display = 'flex';
    } else {
        joinGroupDirect(groupId);
    }
}

async function joinGroupDirect(groupId) {
    try {
        await postJoinGroup(groupId);
        alert("グループに参加しました！");
        runGroupSearch();
    } catch (e) {
        alert("エラー: " + e.message);
    }
}

function closeJoinModal() {
    document.getElementById('join-modal').style.display = 'none';
    joinTargetGroupId = null;
}

async function submitJoinGroup() {
    const password = document.getElementById('join-password').value;
    if (!password) { alert("パスワードを入力してください"); return; }
    try {
        await postJoinGroup(joinTargetGroupId, password);
        alert("グループに参加しました！");
        closeJoinModal();
        runGroupSearch();
    } catch (e) {
        alert("エラー: " + e.message);
    }
}

// ========================================
// group-detail.html: グループ詳細
// ========================================
let currentGroup = null;
let editingProgressId = null;

async function loadGroupDetail() {
    const params = new URLSearchParams(window.location.search);
    const groupId = params.get('id');
    if (!groupId) {
        document.getElementById('group-detail-main').innerHTML = '<p style="color:red; text-align:center; padding:60px;">グループIDが指定されていません</p>';
        return;
    }

    try {
        const [group, progresses] = await Promise.all([
            getGroup(groupId),
            getGroupProgresses(groupId)
        ]);
        currentGroup = group;
        renderGroupDetail(group, progresses);
    } catch (e) {
        const msg = e.message.includes('403') || e.message.includes('403')
            ? 'このグループを閲覧する権限がありません。'
            : 'グループの取得に失敗しました。';
        document.getElementById('group-detail-main').innerHTML = `
            <div style="text-align:center; padding:60px; color:#999;">
                <p style="font-size:2rem; margin-bottom:10px;">🔒</p>
                <p>${msg}</p>
                <a href="/public/index.html" class="add-btn-small">ホームに戻る</a>
            </div>`;
    }
}

function renderGroupDetail(group, progresses) {
    const isOwner = group.owner === currentUser.id;
    const totalPages = group.total_pages || 0;

    // メンバーマップ（user_id → username）
    const memberMap = {};
    (group.members || []).forEach(m => { memberMap[m.id] = m.username; });

    // 全メンバーの進捗バー
    const allSegments = progresses.map(p => {
        const left  = totalPages > 0 ? ((p.start_page - 1) / totalPages) * 100 : 0;
        const width = totalPages > 0 ? ((p.end_page - p.start_page + 1) / totalPages) * 100 : 0;
        const isMe  = p.user_id === currentUser.id;
        return `<div class="range-segment" style="left:${left}%; width:${width}%; background:${isMe ? 'var(--primary-color)' : 'rgba(74,144,226,0.3)'};"></div>`;
    }).join('');

    // 進捗履歴
    const historyHtml = progresses.length === 0
        ? `<p style="color:#999; text-align:center; padding:20px;">まだ進捗がありません</p>`
        : progresses.map(p => {
            const username = memberMap[p.user_id] || '不明';
            const isMe = p.user_id === currentUser.id;
            const canEdit = isMe || isOwner;
            const date = p.created_at ? new Date(p.created_at).toLocaleDateString('ja-JP') : '';

            const fileArea = p.url
                ? `<a href="${p.url}" target="_blank" download style="font-size:0.8rem; color:var(--primary-color);">📎 添付ファイルをダウンロード</a>`
                : (canEdit ? `<label style="font-size:0.8rem; color:#999; cursor:pointer;">
                    📎 ファイルを添付
                    <input type="file" style="display:none;" onchange="handleFileUpload(event, ${group.id}, ${p.id})">
                   </label>` : '');

            const actions = canEdit ? `
                <div style="display:flex; gap:8px; margin-top:8px; align-items:center;">
                    <button onclick="openEditProgressModal(${p.id}, ${p.start_page}, ${p.end_page}, '${escapeHtml(p.memo || '')}')"
                        style="font-size:0.75rem; padding:3px 8px; border:1px solid #ccc; background:#fff; border-radius:4px; cursor:pointer;">✏️ 編集</button>
                    <button onclick="handleDeleteProgress(${group.id}, ${p.id})"
                        style="font-size:0.75rem; padding:3px 8px; border:1px solid #e74c3c; color:#e74c3c; background:#fff; border-radius:4px; cursor:pointer;">🗑️ 削除</button>
                    ${fileArea}
                </div>` : `<div style="margin-top:8px;">${fileArea}</div>`;

            return `
                <div class="history-item">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <span class="badge-page">${p.start_page} 〜 ${p.end_page} P</span>
                            <span style="font-size:0.8rem; color:#999; margin-left:8px;">${date}</span>
                        </div>
                        <span style="font-size:0.8rem; font-weight:bold; color:${isMe ? 'var(--primary-color)' : '#999'};">
                            ${isMe ? '自分' : escapeHtml(username)}
                        </span>
                    </div>
                    ${p.memo ? `<p class="history-memo" style="margin:6px 0 0;">${escapeHtml(p.memo)}</p>` : ''}
                    ${actions}
                </div>`;
        }).join('');

    document.getElementById('group-detail-main').innerHTML = `
        <!-- グループ情報 -->
        <div class="group-summary-card" style="margin-bottom:25px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:15px;">
                <h2 style="margin:0; font-size:1.4rem;">${escapeHtml(group.name)}</h2>
                <div style="display:flex; gap:8px; align-items:center;">
                    ${group.is_lock
                        ? `<span style="font-size:0.8rem; background:#fff3cd; color:#856404; padding:3px 8px; border-radius:10px; border:1px solid #ffc107;">🔒 鍵あり</span>`
                        : `<span style="font-size:0.8rem; background:#d4edda; color:#155724; padding:3px 8px; border-radius:10px; border:1px solid #28a745;">🔓 公開</span>`}
                    <a href="/public/group-setting.html?id=${group.id}"
                        style="font-size:0.8rem; padding:4px 10px; border:1px solid #ccc; border-radius:4px; color:#333;">⚙️ 設定</a>
                </div>
            </div>

            <!-- 課題図書 -->
            ${group.title ? `
            <div style="display:flex; gap:15px; align-items:flex-start; background:#f4f7f6; border-radius:8px; padding:15px; margin-bottom:15px;">
                ${group.cover_url
                    ? `<img src="${group.cover_url}" alt="書影" style="width:70px; height:98px; object-fit:cover; border-radius:4px; flex-shrink:0;">`
                    : `<div style="width:70px; height:98px; background:#eee; border-radius:4px; flex-shrink:0;"></div>`}
                <div>
                    <div style="font-weight:bold; font-size:1.1rem; margin-bottom:5px;">${escapeHtml(group.title)}</div>
                    ${group.author ? `<div style="font-size:0.85rem; color:#777;">👤 ${escapeHtml(group.author)}</div>` : ''}
                    ${group.publisher ? `<div style="font-size:0.85rem; color:#777;">🏢 ${escapeHtml(group.publisher)}</div>` : ''}
                    <div style="font-size:0.85rem; color:#777; margin-top:4px;">📄 ${totalPages} ページ</div>
                </div>
            </div>` : ''}

            <!-- 全メンバーの進捗バー -->
            <div class="progress-container" style="margin-bottom:8px;">
                <span class="progress-text">全メンバーの進捗（青:自分 / 薄青:他メンバー）</span>
                <div class="range-bar-wrapper">${allSegments}</div>
            </div>

            <!-- メンバー一覧 -->
            <div style="font-size:0.85rem; color:#777;">
                👥 ${(group.members || []).length}人参加中：
                ${(group.members || []).map(m =>
                    `<span style="margin-right:8px; ${m.id === group.owner ? 'font-weight:bold; color:var(--primary-color);' : ''}">${escapeHtml(m.username)}${m.id === group.owner ? '（オーナー）' : ''}</span>`
                ).join('')}
            </div>
        </div>

        <!-- 進捗記録フォーム -->
        <div class="input-card" style="margin-bottom:25px;">
            <h3 style="margin:0 0 15px; font-size:1.1rem;">✍️ 進捗を記録する</h3>
            <div class="record-area">
                <div class="progress-input-group">
                    <input type="number" id="detail-start" placeholder="開始" min="1" max="${totalPages}">
                    <span>〜</span>
                    <input type="number" id="detail-end" placeholder="終了" min="1" max="${totalPages}">
                    <span>ページ</span>
                </div>
                <div class="memo-input-group">
                    <input type="text" id="detail-memo" placeholder="メモ（任意）">
                    <button class="btn-record" onclick="submitDetailProgress(${group.id}, ${totalPages})">記録</button>
                </div>
            </div>
        </div>

        <!-- 進捗履歴 -->
        <div class="detail-section" style="background:var(--card-bg); border-radius:8px; padding:20px; box-shadow:0 2px 4px rgba(0,0,0,0.05);">
            <h3 style="margin:0 0 15px; font-size:1.1rem;">📜 進捗履歴</h3>
            <div class="history-list">${historyHtml}</div>
        </div>`;
}

async function submitDetailProgress(groupId, totalPages) {
    const startInput = document.getElementById('detail-start').value;
    const endInput   = document.getElementById('detail-end').value;
    const memo       = document.getElementById('detail-memo').value;
    const startPage  = Number(startInput);
    const endPage    = Number(endInput);

    if (!startInput || !endInput)           { alert("開始・終了ページを入力してください"); return; }
    if (startPage < 1 || endPage < 1)       { alert("1以上のページ数を入力してください"); return; }
    if (startPage > endPage)                { alert("開始ページは終了ページ以下にしてください"); return; }
    if (totalPages > 0 && endPage > totalPages) { alert(`この本は最大 ${totalPages} ページです`); return; }

    try {
        await postGroupProgress(groupId, { start_page: startPage, end_page: endPage, memo });
        alert("記録しました！");
        await loadGroupDetail();
    } catch (e) {
        alert("エラー: " + e.message);
    }
}

function openEditProgressModal(progressId, startPage, endPage, memo) {
    editingProgressId = progressId;
    document.getElementById('edit-start-page').value = startPage;
    document.getElementById('edit-end-page').value   = endPage;
    document.getElementById('edit-memo').value       = memo;
    document.getElementById('edit-progress-modal').style.display = 'flex';
}

function closeEditProgressModal() {
    document.getElementById('edit-progress-modal').style.display = 'none';
    editingProgressId = null;
}

async function submitEditProgress() {
    if (!editingProgressId || !currentGroup) return;
    const startPage = Number(document.getElementById('edit-start-page').value);
    const endPage   = Number(document.getElementById('edit-end-page').value);
    const memo      = document.getElementById('edit-memo').value;

    if (startPage < 1 || endPage < 1)  { alert("1以上のページ数を入力してください"); return; }
    if (startPage > endPage)            { alert("開始ページは終了ページ以下にしてください"); return; }

    try {
        await patchUpdateProgress(currentGroup.id, editingProgressId, { start_page: startPage, end_page: endPage, memo });
        closeEditProgressModal();
        await loadGroupDetail();
    } catch (e) {
        alert("エラー: " + e.message);
    }
}

async function handleDeleteProgress(groupId, progressId) {
    if (!confirm("この進捗を削除しますか？")) return;
    try {
        await deleteProgress(groupId, progressId);
        await loadGroupDetail();
    } catch (e) {
        alert("エラー: " + e.message);
    }
}

async function handleFileUpload(event, groupId, progressId) {
    const file = event.target.files[0];
    if (!file) return;
    try {
        await uploadProgressFile(groupId, progressId, file);
        alert("ファイルをアップロードしました！");
        await loadGroupDetail();
    } catch (e) {
        alert("エラー: " + e.message);
    }
}


// ========================================
// group-setting.html: グループ設定
// ========================================
async function loadGroupSetting() {
    const params = new URLSearchParams(window.location.search);
    const groupId = params.get('id');
    if (!groupId) {
        document.getElementById('group-setting-main').innerHTML = '<p style="color:red; text-align:center; padding:60px;">グループIDが指定されていません</p>';
        return;
    }

    try {
        const group = await getGroup(groupId);
        renderGroupSetting(group);
    } catch (e) {
        document.getElementById('group-setting-main').innerHTML = `
            <div style="text-align:center; padding:60px; color:#999;">
                <p style="font-size:2rem; margin-bottom:10px;">🔒</p>
                <p>このグループの設定を閲覧する権限がありません。</p>
                <a href="/public/index.html" class="add-btn-small">ホームに戻る</a>
            </div>`;
    }
}

function renderGroupSetting(group) {
    const isOwner = group.owner === currentUser.id;

    document.getElementById('group-setting-main').innerHTML = `
        <a href="/public/group-detail.html?id=${group.id}"
            style="color:#999; font-size:0.9rem; display:inline-block; margin-bottom:20px;">◀ グループに戻る</a>

        <h2 style="margin:0 0 25px; font-size:1.3rem;">⚙️ ${escapeHtml(group.name)} の設定</h2>

        <!-- 退会（オーナー以外） -->
        ${!isOwner ? `
        <div style="background:var(--card-bg); border-radius:8px; padding:20px; box-shadow:0 2px 4px rgba(0,0,0,0.05); margin-bottom:20px;">
            <h3 style="margin:0 0 12px; font-size:1rem;">🚪 グループから退会する</h3>
            <p style="font-size:0.9rem; color:#777; margin-bottom:15px;">退会するとこのグループの進捗履歴は閲覧できなくなります。</p>
            <button onclick="handleLeaveGroup(${group.id})"
                style="padding:10px 20px; background:#fff; color:#e74c3c; border:2px solid #e74c3c; border-radius:6px; font-weight:bold; cursor:pointer;">
                退会する
            </button>
        </div>` : ''}


        <!-- オーナー専用設定 -->
        ${isOwner ? `
        <div style="background:var(--card-bg); border-radius:8px; padding:20px; box-shadow:0 2px 4px rgba(0,0,0,0.05); margin-bottom:20px;">
            <h3 style="margin:0 0 15px; font-size:1rem;">✏️ グループ名を変更する</h3>
            <div style="display:flex; gap:10px;">
                <input type="text" id="new-group-name" value="${escapeHtml(group.name)}"
                    style="flex:1; padding:10px; border:1px solid #ccc; border-radius:6px; font-size:1rem; box-sizing:border-box;">
                <button onclick="handleUpdateGroupName(${group.id})" class="btn-record" style="white-space:nowrap; padding:10px 16px;">
                    変更する
                </button>
            </div>
        </div>

        <div style="background:var(--card-bg); border-radius:8px; padding:20px; box-shadow:0 2px 4px rgba(0,0,0,0.05); margin-bottom:20px;">
            <h3 style="margin:0 0 15px; font-size:1rem;">🔒 パスワード設定</h3>
            <div style="margin-bottom:12px;">
                <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
                    <input type="checkbox" id="setting-is-lock" ${group.is_lock ? 'checked' : ''}
                        onchange="toggleSettingPasswordField()">
                    <span>参加にパスワードを設定する</span>
                </label>
            </div>
            <div id="setting-password-field" style="display:${group.is_lock ? 'block' : 'none'};">
                <input type="password" id="setting-password" placeholder="新しいパスワード（変更しない場合は空欄）"
                    style="width:100%; padding:10px; border:1px solid #ccc; border-radius:6px; font-size:1rem; box-sizing:border-box; margin-bottom:10px;">
            </div>
            <button onclick="handleUpdateGroupLock(${group.id})" class="btn-record" style="padding:10px 16px;">
                保存する
            </button>
        </div>

        <!-- グループ削除 -->
        <div style="background:#fff8f8; border:1px solid #f5c6cb; border-radius:8px; padding:20px; margin-top:30px;">
            <h3 style="margin:0 0 10px; font-size:1rem; color:#721c24;">⚠️ 危険な操作</h3>
            <p style="font-size:0.9rem; color:#721c24; margin-bottom:15px;">グループを削除すると、全メンバーの進捗履歴も削除されます。この操作は取り消せません。</p>
            <button onclick="handleDeleteGroup(${group.id})"
                style="padding:10px 20px; background:#fff; color:#e74c3c; border:2px solid #e74c3c; border-radius:6px; font-weight:bold; cursor:pointer;">
                🗑️ グループを削除する
            </button>
        </div>` : ''}
    `;
}

function toggleSettingPasswordField() {
    const isLock = document.getElementById('setting-is-lock').checked;
    document.getElementById('setting-password-field').style.display = isLock ? 'block' : 'none';
}



async function handleUpdateGroupName(groupId) {
    const name = document.getElementById('new-group-name').value.trim();
    if (!name) { alert("グループ名を入力してください"); return; }
    try {
        await patchUpdateGroup(groupId, { name });
        alert("グループ名を変更しました");
        await loadGroupSetting();
    } catch (e) {
        alert("エラー: " + e.message);
    }
}

async function handleUpdateGroupLock(groupId) {
    const isLock   = document.getElementById('setting-is-lock').checked;
    const password = document.getElementById('setting-password').value;
    if (isLock && !password) { alert("パスワードを入力してください"); return; }
    const data = { is_lock: isLock };
    if (password) data.password = password;
    try {
        await patchUpdateGroup(groupId, data);
        alert("設定を保存しました");
        await loadGroupSetting();
    } catch (e) {
        alert("エラー: " + e.message);
    }
}

async function handleLeaveGroup(groupId) {
    if (!confirm("このグループから退会しますか？")) return;
    try {
        await postLeaveGroup(groupId);
        alert("退会しました");
        window.location.href = '/public/index.html';
    } catch (e) {
        alert("エラー: " + e.message);
    }
}

async function handleDeleteGroup(groupId) {
    if (!confirm("本当にグループを削除しますか？\nこの操作は取り消せません。")) return;
    try {
        const res = await fetch(`/api/groups/${groupId}`, { method: 'DELETE' });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "削除に失敗しました");
        }
        alert("グループを削除しました");
        window.location.href = '/public/index.html';
    } catch (e) {
        alert("エラー: " + e.message);
    }
}
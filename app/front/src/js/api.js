// app/front/src/js/api.js
const API_BASE = "/api";

// ========================
// 認証
// ========================
async function getCurrentUser() {
    const res = await fetch(`${API_BASE}/auth/me`);
    if (!res.ok) throw new Error("Unauthorized");
    return res.json();
}

async function postLogout() {
    const res = await fetch(`${API_BASE}/auth/logout`, { method: 'POST' });
    if (!res.ok) throw new Error("ログアウトに失敗しました");
    return res.json();
}

// ========================
// グループ
// ========================
async function getMyGroups() {
    const res = await fetch(`${API_BASE}/groups/my-list`);
    if (!res.ok) throw new Error("グループの取得に失敗しました");
    return res.json();
}

async function getGroup(groupId) {
    const res = await fetch(`${API_BASE}/groups/${groupId}`);
    if (res.status === 403) throw new Error("403");
    if (!res.ok) throw new Error("グループの取得に失敗しました");
    return res.json();
}

async function getAllGroups() {
    const res = await fetch(`${API_BASE}/groups/`);
    if (!res.ok) throw new Error("グループの取得に失敗しました");
    return res.json();
}

async function searchGroupsByName(q) {
    const res = await fetch(`${API_BASE}/groups/search/by-name?q=${encodeURIComponent(q)}`);
    if (res.status === 404) return [];
    if (!res.ok) throw new Error("検索に失敗しました");
    return res.json();
}

async function searchGroupsByBook(q) {
    const res = await fetch(`${API_BASE}/groups/search/by-book?q=${encodeURIComponent(q)}`);
    if (res.status === 404) return [];
    if (!res.ok) throw new Error("検索に失敗しました");
    return res.json();
}

async function postCreateGroup(data) {
    const res = await fetch(`${API_BASE}/groups/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "グループの作成に失敗しました");
    }
    return res.json();
}

async function patchUpdateGroup(groupId, data) {
    const res = await fetch(`${API_BASE}/groups/${groupId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "グループの更新に失敗しました");
    }
    return res.json();
}

async function postJoinGroup(groupId, password = null) {
    const url = password
        ? `${API_BASE}/groups/${groupId}/join?password=${encodeURIComponent(password)}`
        : `${API_BASE}/groups/${groupId}/join`;
    const res = await fetch(url, { method: 'POST' });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "参加に失敗しました");
    }
    return res.json();
}

async function postLeaveGroup(groupId) {
    const res = await fetch(`${API_BASE}/groups/${groupId}/leave`, { method: 'POST' });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "退会に失敗しました");
    }
    return res.json();
}

async function deleteGroup(groupId) {
    const res = await fetch(`${API_BASE}/groups/${groupId}`, { method: 'DELETE' });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "グループの削除に失敗しました");
    }
    return res.json();
}

// ========================
// 進捗
// ========================
async function getGroupProgresses(groupId, limit = null) {
    const url = limit
        ? `${API_BASE}/groups/${groupId}/progress?limit=${limit}`
        : `${API_BASE}/groups/${groupId}/progress`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("進捗の取得に失敗しました");
    return res.json();
}

async function postGroupProgress(groupId, data) {
    const res = await fetch(`${API_BASE}/groups/${groupId}/progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "進捗の記録に失敗しました");
    }
    return res.json();
}

async function patchUpdateProgress(groupId, progressId, data) {
    const res = await fetch(`${API_BASE}/groups/${groupId}/progress/${progressId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "進捗の編集に失敗しました");
    }
    return res.json();
}

async function deleteProgress(groupId, progressId) {
    const res = await fetch(`${API_BASE}/groups/${groupId}/progress/${progressId}`, {
        method: 'DELETE'
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "進捗の削除に失敗しました");
    }
    return res.json();
}

async function uploadProgressFile(groupId, progressId, file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/groups/${groupId}/progress/${progressId}/upload`, {
        method: 'POST',
        body: formData
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "ファイルのアップロードに失敗しました");
    }
    return res.json();
}

// ========================
// 本の検索（Google Books）
// ========================
async function searchGoogleBooksByTitle(q) {
    const res = await fetch(`${API_BASE}/books/search?q=intitle:${encodeURIComponent(q)}`);
    if (!res.ok) throw new Error("本の検索に失敗しました");
    return res.json();
}
async function searchGoogleBooksByAuthor(q) {
    const res = await fetch(`${API_BASE}/books/search?q=inauthor:${encodeURIComponent(q)}`);
    if (!res.ok) throw new Error("本の検索に失敗しました");
    return res.json();
}

/** JWT のペイロードから sub（Supabase user UUID）を取得する */
function parseUserId(jwt: string): string | null {
	try {
		const payload = JSON.parse(atob(jwt.split('.')[1]));
		return payload.sub ?? null;
	} catch {
		return null;
	}
}

/** JWT の有効期限を確認する */
function isJwtExpired(jwt: string): boolean {
	try {
		const payload = JSON.parse(atob(jwt.split('.')[1]));
		return Date.now() / 1000 > payload.exp;
	} catch {
		return true;
	}
}

// Svelte 5 runes で共有状態を管理（.svelte.ts ファイル内で有効）
let _jwt = $state<string | null>(null);
let _userId = $state<string | null>(null);

export const authState = {
	get jwt() {
		return _jwt;
	},
	get userId() {
		return _userId;
	},
	get isLoggedIn() {
		return _jwt !== null;
	}
};

/**
 * localStorage から認証情報を復元する。
 * ブラウザ環境でのみ呼ぶこと（onMount 内）。
 */
export function loadAuthFromStorage(): void {
	const jwt = localStorage.getItem('sts2_jwt');
	if (!jwt || isJwtExpired(jwt)) {
		localStorage.removeItem('sts2_jwt');
		return;
	}
	const userId = parseUserId(jwt);
	if (userId) {
		_jwt = jwt;
		_userId = userId;
	}
}

/**
 * JWT を受け取って認証状態をセットする。
 * URL パラメータからのトークンや登録完了時に呼ぶ。
 */
export function setAuth(jwt: string): boolean {
	if (isJwtExpired(jwt)) return false;
	const userId = parseUserId(jwt);
	if (!userId) return false;

	_jwt = jwt;
	_userId = userId;
	localStorage.setItem('sts2_jwt', jwt);
	return true;
}

export function clearAuth(): void {
	_jwt = null;
	_userId = null;
	localStorage.removeItem('sts2_jwt');
}

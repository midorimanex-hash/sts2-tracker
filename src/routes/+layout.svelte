<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { authState, loadAuthFromStorage, setAuth, clearAuth } from '$lib/auth.svelte';

	let { children } = $props();

	onMount(() => {
		// URLパラメータにトークンがあれば自動ログイン
		const token = $page.url.searchParams.get('token');
		if (token) {
			setAuth(token);
			// トークンをURLから除去（履歴に残さない）
			const url = new URL(window.location.href);
			url.searchParams.delete('token');
			goto(url.pathname + (url.search || ''), { replaceState: true });
		} else {
			loadAuthFromStorage();
		}
	});
</script>

<div class="flex min-h-screen flex-col">
	<!-- ナビゲーション -->
	<nav class="border-b border-[#30363d] bg-[#161b22]">
		<div class="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
			<a href="/" class="flex items-center gap-2 text-lg font-bold text-[#d4a017]">
				<span>⚔</span>
				STS2 Tracker
			</a>
			<div class="flex items-center gap-4 text-sm">
				<a href="/" class="text-[#8b949e] transition hover:text-[#e6edf3]">全体統計</a>
				<a
					href="/me"
					onclick={(e) => {
						e.preventDefault();
						const uid = localStorage.getItem('sts2_uid');
						goto(uid ? `/me?uid=${uid}` : '/me');
					}}
					class="text-[#8b949e] transition hover:text-[#e6edf3]"
				>マイ統計</a>
				<a href="/download" class="text-[#8b949e] transition hover:text-[#e6edf3]">ダウンロード</a>
				{#if authState.isLoggedIn}
					<span class="rounded-full bg-[#21262d] px-3 py-1 text-xs text-[#3fb950]">
						● ログイン中
					</span>
					<button
						onclick={clearAuth}
						class="rounded px-2 py-1 text-xs text-[#8b949e] hover:text-[#f85149]"
					>
						ログアウト
					</button>
				{:else}
					<a
						href="/download"
						class="rounded bg-[#d4a017] px-3 py-1 text-xs font-semibold text-black hover:bg-[#f0c040]"
					>
						はじめる
					</a>
				{/if}
			</div>
		</div>
	</nav>

	<!-- メインコンテンツ -->
	<main class="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
		{@render children()}
	</main>

	<!-- フッター -->
	<footer class="border-t border-[#30363d] py-6 text-center text-xs text-[#8b949e]">
		STS2 Tracker — コミュニティ非公式統計ツール
	</footer>
</div>

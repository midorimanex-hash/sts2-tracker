<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { authState } from '$lib/auth.svelte';
	import { supabase, getAuthClient } from '$lib/supabase';

	type Run = {
		id: string;
		character: string;
		ascension: number;
		win: boolean;
		was_abandoned: boolean;
		killed_by_encounter: string | null;
		played_at: string;
	};

	const charLabel: Record<string, string> = {
		'CHARACTER.IRONCLAD': 'アイアンクラッド',
		'CHARACTER.SILENT': 'サイレント',
		'CHARACTER.DEFECT': 'ディフェクト',
		'CHARACTER.REGENT': 'リージェント',
		'CHARACTER.NECROBINDER': 'ネクロバインダー'
	};

	let loading = $state(true);
	let runs = $state<Run[]>([]);

	// ---- 派生統計 ----
	let totalRuns = $derived(runs.length);
	let wins = $derived(runs.filter((r) => r.win).length);
	let winRate = $derived(totalRuns > 0 ? ((wins / totalRuns) * 100).toFixed(1) : '—');

	// ?uid= があればそのユーザー、なければ自分
	const uidParam = $page.url.searchParams.get('uid');
	const isViewingOther = !!uidParam;
	const displayUserId = $derived(uidParam ?? authState.userId ?? '');

	const UID_KEY = 'sts2_uid';

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleDateString('ja-JP', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	async function loadRuns(userId: string, jwt?: string | null) {
		loading = true;
		const client = jwt ? getAuthClient(jwt) : supabase;
		const { data, error } = await client
			.from('runs')
			.select(
				'id, character, ascension, win, was_abandoned, killed_by_encounter, played_at'
			)
			.eq('user_id', userId)
			.order('played_at', { ascending: false })
			.limit(200);

		if (!error && data) {
			runs = data as Run[];
		}
		loading = false;
	}

	onMount(() => {
		if (uidParam) {
			// ?uid= 指定：localStorageに保存して次回以降も使えるようにする
			localStorage.setItem(UID_KEY, uidParam);
			loadRuns(uidParam);
		} else if (authState.isLoggedIn && authState.userId) {
			// ログイン中：認証クライアントで自分のデータ取得
			loadRuns(authState.userId, authState.jwt);
		} else {
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>STS2 Tracker — マイ統計</title>
</svelte:head>

{#if !isViewingOther && !authState.isLoggedIn}
	<!-- 未ログイン（uid パラメータなし） -->
	<div class="flex flex-col items-center justify-center py-24 text-center">
		<div class="mb-4 text-5xl">⚔</div>
		<h1 class="mb-2 text-2xl font-bold text-[#e6edf3]">ログインが必要です</h1>
		<p class="mb-8 text-sm text-[#8b949e]">
			マイ統計を見るには STS2 Tracker をインストールしてください。<br />
			インストール後、トレイアイコンから「統計を見る」を選ぶと自動でログインされます。
		</p>
		<a
			href="/download"
			class="rounded-lg bg-[#d4a017] px-6 py-3 font-semibold text-black hover:bg-[#f0c040]"
		>
			ダウンロードページへ
		</a>
	</div>
{:else if loading}
	<div class="flex items-center justify-center py-24 text-[#8b949e]">
		<span class="animate-pulse">データを読み込み中...</span>
	</div>
{:else}
	<!-- ヘッダー -->
	<div class="mb-8">
		<h1 class="text-2xl font-bold text-[#e6edf3]">{isViewingOther ? 'ユーザー統計' : 'マイ統計'}</h1>
		<p class="mt-1 font-mono text-xs text-[#8b949e]">ID: {displayUserId}</p>
	</div>

	<!-- サマリーカード -->
	<div class="mb-8 grid grid-cols-3 gap-4">
		<div class="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-4 text-center">
			<p class="text-xs text-[#8b949e]">総ラン数</p>
			<p class="text-2xl font-bold text-[#e6edf3]">{totalRuns}</p>
		</div>
		<div class="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-4 text-center">
			<p class="text-xs text-[#8b949e]">勝利数</p>
			<p class="text-2xl font-bold text-[#3fb950]">{wins}</p>
		</div>
		<div class="rounded-lg border border-[#30363d] bg-[#161b22] px-4 py-4 text-center">
			<p class="text-xs text-[#8b949e]">勝率</p>
			<p class="text-2xl font-bold text-[#d4a017]">{winRate}%</p>
		</div>
	</div>

	<!-- ラン履歴 -->
	<section>
		<h2 class="mb-4 text-lg font-semibold text-[#e6edf3]">ラン履歴</h2>

		{#if runs.length === 0}
			<div class="rounded-lg border border-[#30363d] bg-[#161b22] py-12 text-center text-sm text-[#8b949e]">
				まだラン履歴がありません。STS2 をプレイするとここに表示されます。
			</div>
		{:else}
			<div class="overflow-hidden rounded-lg border border-[#30363d]">
				<table class="w-full text-sm">
					<thead class="bg-[#21262d] text-left text-xs text-[#8b949e]">
						<tr>
							<th class="px-4 py-3">結果</th>
							<th class="px-4 py-3">キャラ</th>
							<th class="px-4 py-3">AC</th>
							<th class="px-4 py-3 hidden sm:table-cell">死因 / 結果</th>
							<th class="px-4 py-3 hidden sm:table-cell text-right">プレイ日時</th>
						</tr>
					</thead>
					<tbody>
						{#each runs as run, i}
							<tr class="border-t border-[#30363d] {i % 2 === 0 ? 'bg-[#161b22]' : 'bg-[#0d1117]'}">
								<td class="px-4 py-3">
									{#if run.was_abandoned}
										<span class="text-[#8b949e]">放棄</span>
									{:else if run.win}
										<span class="font-semibold text-[#3fb950]">勝利</span>
									{:else}
										<span class="font-semibold text-[#f85149]">敗北</span>
									{/if}
								</td>
								<td class="px-4 py-3 text-[#e6edf3]">
									{charLabel[run.character] ?? run.character}
								</td>
								<td class="px-4 py-3 text-[#8b949e]">
									{run.ascension > 0 ? `A${run.ascension}` : '—'}
								</td>
								<td class="hidden px-4 py-3 font-mono text-xs text-[#8b949e] sm:table-cell">
									{run.killed_by_encounter ?? (run.win ? '心臓撃破' : '—')}
								</td>
								<td class="hidden px-4 py-3 text-right text-xs text-[#8b949e] sm:table-cell">
									{formatDate(run.played_at)}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</section>
{/if}

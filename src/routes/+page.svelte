<script lang="ts">
	import { onMount } from 'svelte';
	import { supabase } from '$lib/supabase';

	// ---- 型定義 ----
	type CharStat = { character: string; total: number; wins: number; winRate: number };
	type CardStat = { cardId: string; count: number };
	type RelicStat = { relicId: string; count: number };

	// ---- 状態 ----
	let loading = $state(true);
	let totalRuns = $state(0);
	let charStats = $state<CharStat[]>([]);
	let topCards = $state<CardStat[]>([]);
	let topRelics = $state<RelicStat[]>([]);

	// ---- キャラクター表示名 ----
	const charLabel: Record<string, string> = {
		'CHARACTER.IRONCLAD': 'アイアンクラッド',
		'CHARACTER.SILENT': 'サイレント',
		'CHARACTER.DEFECT': 'ディフェクト',
		'CHARACTER.REGENT': 'リージェント',
		'CHARACTER.NECROBINDER': 'ネクロバインダー'
	};

	// ---- データ取得 ----
	async function loadStats() {
		loading = true;

		// キャラ別勝率
		const { data: runs } = await supabase
			.from('runs')
			.select('character, win')
			.eq('was_abandoned', false)
			.limit(20000);

		if (runs) {
			totalRuns = runs.length;
			const map = new Map<string, { total: number; wins: number }>();
			for (const r of runs) {
				const s = map.get(r.character) ?? { total: 0, wins: 0 };
				s.total++;
				if (r.win) s.wins++;
				map.set(r.character, s);
			}
			charStats = [...map.entries()]
				.map(([character, s]) => ({
					character,
					total: s.total,
					wins: s.wins,
					winRate: s.total > 0 ? (s.wins / s.total) * 100 : 0
				}))
				.sort((a, b) => b.total - a.total);
		}

		// よく使われるカード上位10
		const { data: deckCards } = await supabase
			.from('deck_cards')
			.select('card_id, count')
			.limit(50000);

		if (deckCards) {
			const map = new Map<string, number>();
			for (const c of deckCards) {
				map.set(c.card_id, (map.get(c.card_id) ?? 0) + c.count);
			}
			topCards = [...map.entries()]
				.map(([cardId, count]) => ({ cardId, count }))
				.sort((a, b) => b.count - a.count)
				.slice(0, 10);
		}

		// よく使われるレリック上位10
		const { data: relics } = await supabase
			.from('final_relics')
			.select('relic_id')
			.limit(50000);

		if (relics) {
			const map = new Map<string, number>();
			for (const r of relics) {
				map.set(r.relic_id, (map.get(r.relic_id) ?? 0) + 1);
			}
			topRelics = [...map.entries()]
				.map(([relicId, count]) => ({ relicId, count }))
				.sort((a, b) => b.count - a.count)
				.slice(0, 10);
		}

		loading = false;
	}

	onMount(loadStats);
</script>

<svelte:head>
	<title>STS2 Tracker — 全体統計</title>
</svelte:head>

<!-- ヘッダー -->
<div class="mb-8">
	<h1 class="text-2xl font-bold text-[#e6edf3]">全体統計</h1>
	<p class="mt-1 text-sm text-[#8b949e]">全ユーザーの集計データ</p>
</div>

{#if loading}
	<div class="flex items-center justify-center py-24 text-[#8b949e]">
		<span class="animate-pulse">データを読み込み中...</span>
	</div>
{:else}
	<!-- 総ラン数 -->
	<div class="mb-8 rounded-lg border border-[#30363d] bg-[#161b22] px-6 py-4">
		<p class="text-sm text-[#8b949e]">総ラン数</p>
		<p class="text-3xl font-bold text-[#d4a017]">{totalRuns.toLocaleString()}</p>
	</div>

	<!-- キャラ別勝率 -->
	<section class="mb-8">
		<h2 class="mb-4 text-lg font-semibold text-[#e6edf3]">キャラ別勝率</h2>
		<div class="grid gap-3 sm:grid-cols-2">
			{#each charStats as s}
				<div class="rounded-lg border border-[#30363d] bg-[#161b22] p-4">
					<div class="mb-2 flex items-center justify-between">
						<span class="font-semibold text-[#e6edf3]">
							{charLabel[s.character] ?? s.character}
						</span>
						<span class="text-sm text-[#8b949e]">{s.total.toLocaleString()} ラン</span>
					</div>
					<!-- プログレスバー -->
					<div class="mb-1 h-2 w-full overflow-hidden rounded-full bg-[#21262d]">
						<div
							class="h-2 rounded-full bg-[#3fb950] transition-all"
							style="width: {s.winRate.toFixed(1)}%"
						></div>
					</div>
					<div class="flex justify-between text-sm">
						<span class="text-[#3fb950] font-semibold">{s.winRate.toFixed(1)}%</span>
						<span class="text-[#8b949e]">{s.wins}勝 / {s.total - s.wins}敗</span>
					</div>
				</div>
			{/each}
		</div>
	</section>

	<!-- よく使われるカード / レリック -->
	<div class="grid gap-6 sm:grid-cols-2">
		<!-- カード上位10 -->
		<section>
			<h2 class="mb-4 text-lg font-semibold text-[#e6edf3]">よく使われるカード TOP10</h2>
			<div class="rounded-lg border border-[#30363d] bg-[#161b22] overflow-hidden">
				{#each topCards as c, i}
					<div
						class="flex items-center justify-between px-4 py-2.5 text-sm
						{i % 2 === 0 ? '' : 'bg-[#21262d]'}"
					>
						<div class="flex items-center gap-3">
							<span class="w-5 text-right text-[#8b949e]">{i + 1}</span>
							<span class="font-mono text-[#e6edf3]">{c.cardId}</span>
						</div>
						<span class="text-[#8b949e]">{c.count.toLocaleString()}</span>
					</div>
				{/each}
				{#if topCards.length === 0}
					<p class="px-4 py-6 text-center text-sm text-[#8b949e]">データがありません</p>
				{/if}
			</div>
		</section>

		<!-- レリック上位10 -->
		<section>
			<h2 class="mb-4 text-lg font-semibold text-[#e6edf3]">よく使われるレリック TOP10</h2>
			<div class="rounded-lg border border-[#30363d] bg-[#161b22] overflow-hidden">
				{#each topRelics as r, i}
					<div
						class="flex items-center justify-between px-4 py-2.5 text-sm
						{i % 2 === 0 ? '' : 'bg-[#21262d]'}"
					>
						<div class="flex items-center gap-3">
							<span class="w-5 text-right text-[#8b949e]">{i + 1}</span>
							<span class="font-mono text-[#e6edf3]">{r.relicId}</span>
						</div>
						<span class="text-[#8b949e]">{r.count.toLocaleString()}</span>
					</div>
				{/each}
				{#if topRelics.length === 0}
					<p class="px-4 py-6 text-center text-sm text-[#8b949e]">データがありません</p>
				{/if}
			</div>
		</section>
	</div>
{/if}

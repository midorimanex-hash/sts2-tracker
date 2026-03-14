<script lang="ts">
	// ダウンロードリンクは正式リリース後に更新
	const RELEASE_URL = '#';
	const VERSION = '準備中';
</script>

<svelte:head>
	<title>STS2 Tracker — ダウンロード</title>
</svelte:head>

<!-- ヒーロー -->
<div class="mb-12 text-center">
	<div class="mb-4 text-6xl">⚔</div>
	<h1 class="mb-2 text-3xl font-bold text-[#e6edf3]">STS2 Tracker</h1>
	<p class="text-[#8b949e]">Slay the Spire 2 の統計を自動で記録するツール</p>
</div>

<!-- ダウンロードボタン -->
<div class="mb-12 flex justify-center">
	<a
		href={RELEASE_URL}
		class="flex flex-col items-center rounded-xl border border-[#d4a017] bg-[#161b22]
		px-10 py-6 text-center transition hover:bg-[#21262d]"
	>
		<span class="mb-1 text-4xl">⬇</span>
		<span class="text-lg font-bold text-[#d4a017]">Windows 版をダウンロード</span>
		<span class="mt-1 text-sm text-[#8b949e]">STS2Tracker-{VERSION}.exe</span>
	</a>
</div>

<!-- インストール手順 -->
<section class="mb-10">
	<h2 class="mb-6 text-xl font-bold text-[#e6edf3]">インストール方法</h2>
	<ol class="space-y-4">
		{#each [
			{ n: 1, title: 'exeをダウンロード', desc: '上のボタンから STS2Tracker.exe をダウンロードします。' },
			{ n: 2, title: 'exeを起動', desc: '好きな場所に置いてダブルクリックで起動します。インストール作業は不要です。' },
			{ n: 3, title: '自動でデータ収集開始', desc: 'タスクトレイにアイコンが表示されます。STS2 を起動するとセーブファイルを自動で検出して記録が始まります。' },
			{ n: 4, title: '統計を見る', desc: 'タスクトレイアイコンを右クリック →「統計を見る」でブラウザが開き、自動でログインされます。' }
		] as step}
			<li class="flex gap-4 rounded-lg border border-[#30363d] bg-[#161b22] px-5 py-4">
				<span
					class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#d4a017] font-bold text-black text-sm"
				>
					{step.n}
				</span>
				<div>
					<p class="font-semibold text-[#e6edf3]">{step.title}</p>
					<p class="mt-0.5 text-sm text-[#8b949e]">{step.desc}</p>
				</div>
			</li>
		{/each}
	</ol>
</section>

<!-- FAQ -->
<section class="mb-10">
	<h2 class="mb-6 text-xl font-bold text-[#e6edf3]">よくある質問</h2>
	<div class="space-y-3">
		{#each [
			{
				q: 'アカウント登録は必要ですか？',
				a: '不要です。exe を起動すると自動で匿名アカウントが作成されます。メールアドレスやパスワードは一切不要です。'
			},
			{
				q: '個人情報は収集されますか？',
				a: 'Steam ID・ユーザー名などの個人を特定できる情報は一切収集しません。収集するのはゲームのプレイデータのみです。'
			},
			{
				q: 'セーブファイルを直接送信しているのですか？',
				a: 'セーブファイルの内容（統計データ）のみをサーバーに送信します。ファイル自体はPC上に残ります。'
			},
			{
				q: 'STS2 が起動していないときはどうなりますか？',
				a: 'ツールはタスクトレイで待機しますが、STS2 が起動していない間はファイル監視をしません。ゲームを起動すると自動で監視が再開されます。'
			}
		] as item}
			<details class="rounded-lg border border-[#30363d] bg-[#161b22]">
				<summary class="cursor-pointer px-5 py-4 font-semibold text-[#e6edf3] hover:text-[#d4a017]">
					{item.q}
				</summary>
				<p class="px-5 pb-4 text-sm text-[#8b949e]">{item.a}</p>
			</details>
		{/each}
	</div>
</section>

<!-- 技術情報 -->
<section class="rounded-lg border border-[#30363d] bg-[#161b22] px-5 py-4 text-sm text-[#8b949e]">
	<p class="mb-1 font-semibold text-[#e6edf3]">動作環境</p>
	<ul class="list-inside list-disc space-y-1">
		<li>Windows 10 / 11 (64bit)</li>
		<li>Slay the Spire 2（Steam版）</li>
		<li>インターネット接続（データ送信のため）</li>
	</ul>
</section>

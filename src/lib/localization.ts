import encounterData from './localization/encounters.json';
import cardData from './localization/cards.json';

const encounters = encounterData as Record<string, string>;
const cards = cardData as Record<string, string>;

/**
 * エンカウンターIDを日本語名に変換する。
 * 例: "ENCOUNTER.DECIMILLIPEDE_ELITE" → "万足ムカデ"
 *     "DECIMILLIPEDE_ELITE"           → "万足ムカデ"（プレフィックスなしも対応）
 * 不明なIDはそのまま返す。
 */
export function getEncounterName(id: string | null | undefined): string {
	if (!id) return '—';
	const key = id.startsWith('ENCOUNTER.') ? id.slice('ENCOUNTER.'.length) : id;
	return encounters[`${key}.title`] ?? id;
}

/**
 * カードIDを日本語名に変換する。
 * 例: "CARD.BASH" → "バッシュ"
 *     "BASH"      → "バッシュ"（プレフィックスなしも対応）
 * 不明なIDはそのまま返す。
 */
export function getCardName(id: string | null | undefined): string {
	if (!id) return '—';
	const key = id.startsWith('CARD.') ? id.slice('CARD.'.length) : id;
	return cards[`${key}.title`] ?? id;
}

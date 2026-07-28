# Codex Reset Watch

A private Next.js app that checks recent public posts from `@thsottiaux` and determines whether a credible Codex usage reset is available or announced for the near future.

## No paid X developer account

The live provider reads the account's public RSS feed through a small list of public mirrors. It tries each mirror in order and reports `unavailable` when all mirrors fail. No X API key, bearer token, or paid developer account is required.

This is deliberately best-effort. Public mirrors can be blocked, rate-limited, or disappear. The UI never treats a failed fetch as "no reset"; it reports that the source is unavailable.

## Scoring safeguards

A post can qualify only when all three are present:

1. An explicit Codex reference.
2. A usage-related concept such as limits, credits, extra access, or free usage.
3. A granting action such as reset, replenish, increase, restore, or make free.

A post containing only the word `reset` cannot qualify. Negative rules reject password, laptop, device, server, and database resets.

## Status thresholds

- **Confirmed**: score of 72 or more, all three safety gates satisfied, no future-only wording.
- **Upcoming**: score of 68 or more, all three safety gates satisfied, explicit future timeframe.
- **Possible**: score of 50 or more, all three safety gates satisfied.
- **None**: no qualifying post in the last 14 days.
- **Unavailable**: every public RSS mirror failed.

## Local setup

```bash
cp .env.example .env.local
npm install
npm run dev
```

Use `POST_PROVIDER=mock` for local testing, or `POST_PROVIDER=rss` for live public data.

## Vercel variables

```env
POST_PROVIDER=rss
X_USERNAME=thsottiaux
NITTER_INSTANCES=https://xcancel.com,https://nitter.poast.org,https://nitter.privacydev.net
CRON_SECRET=<random secret>
```

Only `CRON_SECRET` is sensitive. Never commit real secrets; `.env*` files are ignored.

---
title: "About"
seoTitle: "About: software developer building MCP servers and AI agents · Furkan Köykıran"
url: /en/about/
layout: about
description: "Who is Furkan Köykıran? From small Python bots to MCP servers and AI agents, the work and collaborations he is looking for, and how to reach him."
lead: "I'm a recent graduate and software developer working on AI agents, developer tools and automation. I'm looking for work, and getting ready to start my own company."
ogKicker: "About"
ogTitle: "Software developer building MCP servers and AI agents"
---

## How I started

I got into programming through automation. The first things I wrote were small Python bots that did repetitive jobs for me in the games I played and the Telegram channels I followed: a bot that copied channel posts, another that forwarded anonymous messages to a group, a blacklist system for a game community.

Then I moved on to crypto markets: data collectors, price trackers and trading bots. That period taught me to deal with APIs, to handle errors properly, and to write code that runs all night and is still up in the morning. I've left the projects from those years as they are, under "Early projects" on the [projects page](/en/projects/#early).

## What I do now

Most of my time goes into AI agents. I write [Model Context Protocol](https://modelcontextprotocol.io/) servers: small TypeScript services that let an agent like Claude, Cursor or Cline talk to [DEV Community](/en/projects/devto-mcp/), [Freqtrade](/en/projects/freqtrade-mcp/), Upwork or Whop. Most of them are published as npm packages.

I also turned my own Claude Code setup into a [toolkit](/en/projects/claude/) anyone can install with one command. Every skill is pinned to a reviewed commit and updates arrive as pull requests. Besides that I've built gateways for Codex and Gemini, a [trending repositories list](https://furkankoykiran.com.tr/awesome-trending-repos/) that updates itself every day, and [Quorum](/en/projects/quorum/), a multi-agent trading committee that votes on every trade.

When I run into a problem in an open-source tool I use, I fix it and send a pull request. I fixed header parsing and malformed Unicode bugs in Microsoft Playwright's MCP code, added Goose agent support to GitHub spec-kit, and closed leaking HTTP response bodies in keploy. The full list is on the [contributions page](/en/contributions/).

## What I'm into

The projects on this site are only the public part of what I work on. My private repositories cover the same ground:

- **Memory and context for coding agents.** Systems that keep what an agent learned in earlier sessions and build the next prompt with the right files and constraints. Also human-approved agents that turn a circuit described in plain language into a schematic file, or draft a patch for an issue and test it in a sandbox.
- **Algorithmic trading and quantitative analysis.** Services that parse trading signals and check their numbers, backtest engines, strategy comparisons for forex and crypto, and decision pipelines where several agents argue over the news before a prediction-market trade.
- **Telegram bots and Mini Apps.** Community management, consent-first invite flows, a language-learning bot on Cloudflare Workers, media download and game bots.
- **Infrastructure and self-hosting.** Docker Compose, Traefik, Cloudflare Tunnel, Workers and D1, environments managed with GitOps, monitoring.
- **Games and simulation.** Rebuilding a browser-based political and economic nation simulation with NestJS and Next.js, and a quiet logic puzzle in Godot.
- **Security and abuse prevention.** Server-side bot detection and risk scoring, a generator for RFC 9116 security.txt files, and scope-checked automation for authorized testing.

## What I'm looking for

- **A full-time job.** A team working on AI agents, developer tools, Python backends or automation. I'm comfortable taking on broad responsibility in a small team.
- **Freelance projects and collaborations.** If you need an MCP server, an integration or some automation, let's talk.
- **My own company.** Longer term I want to build a product company, so I care about more than writing code: talking to users and seeing a piece of work through to the end. If you're thinking about something similar, write to me.

## Writing

I write about what I learn on [my blog](https://blog.furkankoykiran.com.tr/en/), in Turkish and English: MCP, open-source contributions, trading bots in Python, and DevOps. The English versions are also cross-posted to dev.to.

## Contact {#contact}

E-mail is the fastest way: {{< email >}}. You can also find me on these accounts.

{{< socials >}}

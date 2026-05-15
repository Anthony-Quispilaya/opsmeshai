import http from "node:http";
import { randomUUID } from "node:crypto";

import { Spectrum, cloud } from "spectrum-ts";
import { terminal } from "spectrum-ts/providers/terminal";
import { imessage } from "spectrum-ts/providers/imessage";
import { whatsappBusiness } from "spectrum-ts/providers/whatsapp-business";
import { createClient as createWhatsappClient } from "@photon-ai/whatsapp-business";
import { createClient as createIMessageClient } from "@photon-ai/advanced-imessage";

try {
  process.loadEnvFile(".env");
} catch (error) {
  if (error?.code !== "ENOENT") throw error;
}

const PORT = Number(process.env.PHOTON_BRIDGE_PORT || "8787");
const CALLBACK_URL = (() => {
  if (process.env.PHOTON_CALLBACK_URL) return process.env.PHOTON_CALLBACK_URL;
  if (process.env.API_URL) {
    return new URL("/api/v1/messaging/photon/events", process.env.API_URL).toString();
  }
  return "http://127.0.0.1:8000/api/v1/messaging/photon/events";
})();
const CALLBACK_TOKEN = process.env.PHOTON_BRIDGE_TOKEN || "dev-bridge-token";
const DEFAULT_THREAD_ID = process.env.PHOTON_BRIDGE_THREAD_ID || "";

const projectId = process.env.PHOTON_PROJECT_ID;
const projectSecret = process.env.PHOTON_PROJECT_SECRET;

let app;
if (projectId && projectSecret) {
  try {
    app = await Spectrum({
      projectId,
      projectSecret,
      providers: [terminal.config(), imessage.config()],
    });
  } catch (error) {
    const detail = String(error?.message || error);
    if (detail.includes("iMessage is not enabled")) {
      console.warn(
        "[photon-bridge] iMessage provider not enabled in Photon project yet; starting bridge in terminal-only mode.",
      );
      app = await Spectrum({
        projectId,
        projectSecret,
        providers: [terminal.config()],
      });
    } else if (detail.includes("WhatsApp Business is not enabled")) {
      app = await Spectrum({
        projectId,
        projectSecret,
        providers: [terminal.config(), imessage.config()],
      });
    } else {
      throw error;
    }
  }
} else {
  app = await Spectrum({
    providers: [terminal.config()],
  });
}

let latestSpace = null;
let latestSpaceObj = null;

async function sendWhatsAppDirect(to, messageText) {
  if (!projectId || !projectSecret) {
    throw new Error("Missing PHOTON_PROJECT_ID/PHOTON_PROJECT_SECRET");
  }

  const tokenData = await cloud.issueWhatsappBusinessTokens(projectId, projectSecret);
  const firstPhoneNumberId = Object.keys(tokenData.auth || {})[0];
  if (!firstPhoneNumberId) {
    throw new Error("No WhatsApp Business line is configured in this Photon project");
  }

  const accessToken = tokenData.auth[firstPhoneNumberId];
  const client = createWhatsappClient({
    accessToken,
    appSecret: "",
    phoneNumberId: firstPhoneNumberId,
  });

  try {
    const sent = await client.messages.send({ to, text: messageText });
    return sent?.messageId || `bridge-${randomUUID()}`;
  } finally {
    await client.close().catch(() => {});
  }
}

async function sendIMessageDirect(to, messageText) {
  if (!projectId || !projectSecret) {
    throw new Error("Missing PHOTON_PROJECT_ID/PHOTON_PROJECT_SECRET");
  }

  const tokenData = await cloud.issueImessageTokens(projectId, projectSecret);
  let remote;
  if (tokenData.type === "shared") {
    const address = process.env.SPECTRUM_IMESSAGE_ADDRESS || "imessage.spectrum.photon.codes:443";
    remote = createIMessageClient({
      address,
      tls: true,
      token: async () => tokenData.token,
    });
  } else {
    const first = Object.entries(tokenData.auth || {})[0];
    if (!first) {
      throw new Error("No dedicated iMessage client token available");
    }
    const [instanceId, token] = first;
    remote = createIMessageClient({
      address: `${instanceId}.imsg.photon.codes:443`,
      tls: true,
      token: async () => token,
    });
  }

  try {
    const sent = await remote.messages.sendText(`any;-;${to}`, messageText);
    return sent?.guid || `bridge-${randomUUID()}`;
  } finally {
    await remote.close().catch(() => {});
  }
}

async function postCallback(body) {
  try {
    await fetch(CALLBACK_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-photon-bridge-token": CALLBACK_TOKEN,
      },
      body: JSON.stringify(body),
    });
  } catch (error) {
    console.error("Photon callback failed:", error);
  }
}

void (async () => {
  for await (const [space, message] of app.messages) {
    latestSpace = {
      id: space.id,
      platform: message.platform,
    };
    latestSpaceObj = space;
    if (message.content.type !== "text") continue;

    await postCallback({
      event_id: `photon-${message.id}`,
      provider_message_id: message.id,
      thread_id: DEFAULT_THREAD_ID || `inbound-${message.platform}-${message.sender.id}`,
      sender: message.sender.id,
      text: message.content.text,
      platform: message.platform,
    });
  }
})();

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || "/", `http://127.0.0.1:${PORT}`);

  if (req.method === "GET" && url.pathname === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        ok: true,
        callbackUrl: CALLBACK_URL,
        hasDefaultThread: Boolean(DEFAULT_THREAD_ID),
      }),
    );
    return;
  }

  if (req.method === "POST" && url.pathname === "/send") {
    if (req.headers["x-photon-bridge-token"] !== CALLBACK_TOKEN) {
      res.writeHead(401, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ detail: "Invalid bridge token" }));
      return;
    }

    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const body = JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
    const text = String(body.text || "").trim();
    if (!text) {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ detail: "Missing text payload" }));
      return;
    }
    const channel = String(body.channel || "sms").toLowerCase();
    const recipient = String(body.recipient || "").trim();

    let targetSpace = latestSpaceObj;
    let targetMeta = latestSpace;

    if (channel === "whatsapp" && recipient) {
      try {
        const providerMessageId = await sendWhatsAppDirect(recipient, text);
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            status: "sent",
            provider_message_id: providerMessageId,
            bridge_mode: "photon_sdk",
            space_id: recipient,
            platform: "WhatsApp Business",
          }),
        );
      } catch (error) {
        res.writeHead(502, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            detail: `Photon send failed: ${error?.message || String(error)}`,
          }),
        );
      }
      return;
    }

    if (channel === "imessage" && recipient) {
      try {
        const providerMessageId = await sendIMessageDirect(recipient, text);
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            status: "sent",
            provider_message_id: providerMessageId,
            bridge_mode: "photon_sdk",
            space_id: recipient,
            platform: "iMessage",
          }),
        );
      } catch (error) {
        res.writeHead(502, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            detail: `Photon send failed: ${error?.message || String(error)}`,
          }),
        );
      }
      return;
    }

    if (!targetSpace || !targetMeta) {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          detail:
            "No active Spectrum space yet. For WhatsApp, pass recipient and channel=whatsapp; otherwise send one inbound message first.",
        }),
      );
      return;
    }

    try {
      await app.send(targetSpace, text);
    } catch (error) {
      res.writeHead(502, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          detail: `Photon send failed: ${error?.message || String(error)}`,
        }),
      );
      return;
    }

    const providerMessageId = `bridge-${randomUUID()}`;
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(
      JSON.stringify({
        status: "sent",
        provider_message_id: providerMessageId,
        bridge_mode: "photon_sdk",
        space_id: targetMeta.id,
        platform: targetMeta.platform,
      }),
    );
    return;
  }

  res.writeHead(404, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ detail: "Not found" }));
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`Photon bridge listening on http://127.0.0.1:${PORT}`);
});

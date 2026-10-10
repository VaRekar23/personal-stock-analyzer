import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

const client = axios.create({ baseURL: API, timeout: 60000 });

export const api = {
  health: () => client.get("/health").then((r) => r.data),
  marketOverview: () => client.get("/market/overview").then((r) => r.data),
  instruments: () => client.get("/instruments").then((r) => r.data),
  quote: (symbol) => client.get(`/quote/${symbol}`).then((r) => r.data),
  candles: (symbol, interval = "1d", count = 200) =>
    client.get(`/candles/${symbol}`, { params: { interval, count } }).then((r) => r.data),
  analyze: (payload) => client.post("/analyze", payload).then((r) => r.data),
  history: (symbol) => client.get(`/analysis/history/${symbol}`).then((r) => r.data),
  scan: (mode) => client.get("/scan", { params: { mode } }).then((r) => r.data),
  portfolio: () => client.get("/portfolio").then((r) => r.data),
  fundamentals: (symbol) => client.get(`/fundamentals/${symbol}`).then((r) => r.data),
  news: (symbol) => client.get(`/news/${symbol}`).then((r) => r.data),
  evalsRun: (sample_size = 6) =>
    client.post("/evals/run", { sample_size }).then((r) => r.data),
  evalsLatest: () => client.get("/evals/latest").then((r) => r.data),
  settings: () => client.get("/settings").then((r) => r.data),
  updateSettings: (section, values) =>
    client.put(`/settings/${section}`, { values }).then((r) => r.data),
  kiteStatus: () => client.get("/kite/status").then((r) => r.data),
  kiteLoginUrl: () => client.get("/kite/login-url").then((r) => r.data),
  kiteConnect: (request_token) =>
    client.post("/kite/session", { request_token }).then((r) => r.data),
  kiteLogout: () => client.post("/kite/logout").then((r) => r.data),
  knowledgeDocuments: (symbol) =>
    client.get("/knowledge/documents", { params: symbol ? { symbol } : {} }).then((r) => r.data),
  knowledgeDelete: (id) => client.delete(`/knowledge/documents/${id}`).then((r) => r.data),
  knowledgeUpload: (formData) =>
    client.post("/knowledge/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then((r) => r.data),
  research: (body) => client.post("/research", body).then((r) => r.data),
  backtestOptions: () => client.get("/backtests/options").then((r) => r.data),
  backtestCoverage: (body) => client.post("/backtests/coverage", body).then((r) => r.data),
  backtestPrepare: (body) => client.post("/backtests/prepare", body, { timeout: 300000 }).then((r) => r.data),
  backtestCreate: (body) => client.post("/backtests", body).then((r) => r.data),
  backtestList: () => client.get("/backtests").then((r) => r.data),
  backtestGet: (id) => client.get(`/backtests/${id}`).then((r) => r.data),
  strategyEvals: () => client.get("/evals/strategy").then((r) => r.data),
};

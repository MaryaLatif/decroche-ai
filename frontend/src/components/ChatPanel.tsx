import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import type { FormEvent } from "react";
import { confirmOrder, sendMessage, startConversation } from "../api/onboarding";
import type { Cart, Order } from "../types/knowledge";
import BackButton from "./BackButton";

interface Msg { role: "user" | "assistant"; text: string }

export default function ChatPanel({ businessId, onBack }: { businessId: string; onBack: () => void }) {
    const [convId, setConvId] = useState<string | null>(null);
    const [messages, setMessages] = useState<Msg[]>([]);
    const [cart, setCart] = useState<Cart | null>(null);
    const [order, setOrder] = useState<Order | null>(null);
    const [input, setInput] = useState("");
    const [name, setName] = useState("");
    const [phone, setPhone] = useState("");
    const [sending, setSending] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const started = useRef(false);
    const bottom = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (started.current) return;
        started.current = true;
        startConversation(businessId)
            .then((r) => { setConvId(r.conversation_id); setMessages([{ role: "assistant", text: r.greeting }]); })
            .catch((e) => setError(e.message));
    }, [businessId]);

    useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

    const eur = (cents: number, cur = "EUR") =>
        (cents / 100).toLocaleString("fr-FR", { style: "currency", currency: cur });

    async function send(e: FormEvent) {
        e.preventDefault();
        if (!convId || !input.trim() || sending) return;
        const text = input.trim();
        setInput(""); setError(null); setSending(true);
        setMessages((m) => [...m, { role: "user", text }]);
        try {
            const r = await sendMessage(businessId, convId, text);
            setMessages((m) => [...m, { role: "assistant", text: r.reply }]);
            setCart(r.cart);
        } catch (err) { setError((err as Error).message); }
        finally { setSending(false); }
    }

    async function confirm() {
        if (!convId) return;
        setError(null);
        try {
            const r = await confirmOrder(businessId, convId, name, phone);
            setOrder(r.order); setCart(null);
        } catch (err) { setError((err as Error).message); }
    }

    return (
        <>
            <BackButton onClick={onBack} label="Modifier le catalogue" />
            <div className="chat-layout">
                <section className="chat-box">
                    <div className="chat-messages">
                        {messages.map((m, i) =>
                            m.role === "assistant" ? (
                                <div key={i} className="bubble assistant"><ReactMarkdown>{m.text}</ReactMarkdown></div>
                            ) : (
                                <div key={i} className="bubble user">{m.text}</div>
                            ),
                        )}
                        {sending && <div className="bubble assistant">…</div>}
                        <div ref={bottom} />
                    </div>
                    {error && <p className="error" style={{ margin: 12 }}>{error}</p>}
                    <form className="chat-input" onSubmit={send}>
                        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Votre message…" maxLength={1000} />
                        <button disabled={sending || !convId}>Envoyer</button>
                    </form>
                </section>

                <aside className="details-card cart">
                    <h2 style={{ marginTop: 0 }}>Panier</h2>
                    {order ? (
                        <p>Demande <strong>{order.number}</strong> enregistrée ({eur(order.total_cents, order.currency)}). Elle reste en attente d'acceptation par le commerce.</p>
                    ) : cart && cart.lines.length ? (
                        <>
                            <ul className="rows">
                                {cart.lines.map((l) => (
                                    <li key={l.item_id} className="row">
                                        <span>{l.quantity} × {l.name}</span>
                                        <span className="right">{eur(l.line_total_cents, cart.currency)}</span>
                                    </li>
                                ))}
                            </ul>
                            <div className="total"><span>Total</span><span>{eur(cart.total_cents, cart.currency)}</span></div>
                            <input placeholder="Nom" value={name} onChange={(e) => setName(e.target.value)} />
                            <input placeholder="Téléphone" value={phone} onChange={(e) => setPhone(e.target.value)} />
                            <button className="primary" onClick={confirm} disabled={!name || phone.length < 6}>
                                Confirmer la commande (retrait)
                            </button>
                        </>
                    ) : (
                        <p className="muted">Panier vide.</p>
                    )}
                </aside>
            </div>
        </>
    );
}
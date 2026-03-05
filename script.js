let betPerLine = 1;
let autoRemaining = 0;
let spinning = false;

const symbolsAnim = ["🍒","🍋","🔔","⭐","💎","🃏","🌟","🎁"];

function $(id){ return document.getElementById(id); }

function safePlay(audioEl){
    try { audioEl.currentTime = 0; audioEl.play(); } catch(e) {}
}

function clearHighlights(){
    document.querySelectorAll(".cell").forEach(c=>{
        c.classList.remove("win");
        c.classList.remove("payline");
    });
}

function highlightWinningLines(winningLines){
    if(!Array.isArray(winningLines) || winningLines.length === 0) return;

    let i = 0;
    function showNext(){
        if(i >= winningLines.length) return;
        clearHighlights();

        const line = winningLines[i];
        for(const [r,c] of line.cells){
            const cell = $("c"+r+c);
            if(cell){
                cell.classList.add("payline");
                cell.classList.add("win");
            }
        }
        i++;
        setTimeout(showNext, 500);
    }
    showNext();
}

function jackpotExplosion(){
    const container = $("explosion");
    container.innerHTML = "";
    container.style.display = "block";

    const emojis = ["💎","✨","💰","🎉","🔥"];
    for(let i=0;i<60;i++){
        const p = document.createElement("div");
        p.className = "particle";
        p.textContent = emojis[Math.floor(Math.random()*emojis.length)];

        p.style.left = Math.random()*100 + "%";
        p.style.top  = Math.random()*100 + "%";
        p.style.setProperty("--x", (Math.random()*600-300) + "px");
        p.style.setProperty("--y", (Math.random()*600-300) + "px");
        container.appendChild(p);
    }

    setTimeout(()=>{ container.style.display="none"; }, 1100);
}

function setBet(value){
    betPerLine = value;
    document.querySelectorAll(".betbtn").forEach(b=>{
        b.classList.toggle("active", Number(b.dataset.bet) === value);
    });
}

function renderGrid(grid){
    for(let r=0;r<3;r++){
        for(let c=0;c<5;c++){
            $("c"+r+c).textContent = grid[r][c];
        }
    }
}

function startAnimation(){
    return setInterval(()=>{
        for(let r=0;r<3;r++){
            for(let c=0;c<5;c++){
                $("c"+r+c).textContent = symbolsAnim[Math.floor(Math.random()*symbolsAnim.length)];
            }
        }
    }, 70);
}

function showBonusOverlay(amount){
    const overlay = $("bonusOverlay");
    overlay.classList.remove("hidden");
    $("result").textContent = `🎁 BONUS WIN +${amount}`;
}

function hideBonusOverlay(){
    $("bonusOverlay").classList.add("hidden");
}

async function spin(){
    if(spinning) return;
    spinning = true;

    clearHighlights();
    $("result").textContent = "";
    safePlay($("spinSound"));

    const anim = startAnimation();

    try{
        const res = await fetch(`/spin?bet=${betPerLine}`);
        const data = await res.json();

        setTimeout(()=>{
            clearInterval(anim);

            if(data.error){
                $("result").textContent = "❌ Not enough coins";
                autoRemaining = 0;
                spinning = false;
                return;
            }

            renderGrid(data.grid);

            $("coins").textContent = data.coins;
            $("freespins").textContent = data.free_spins;
            $("jackpot").textContent = data.jackpot;

            if(data.stats){
                $("spins").textContent = data.stats.spins;
                $("wins").textContent = data.stats.wins;
                $("bigwin").textContent = data.stats.biggest;
            }

            let msg = [];
            if(data.is_free) msg.push("🎁 FREE SPIN");
            else msg.push(`💸 -${data.cost} (Bet ${data.bet_per_line}×${data.lines})`);

            if(data.scatter_count >= 3) msg.push(`🌟 SCATTER x${data.scatter_count}`);

            if(data.bonus_trigger) msg.push(`🎁 BONUS +${data.bonus_win}`);

            if(data.win){
                if(data.jackpot_won){
                    safePlay($("jackpotSound"));
                    jackpotExplosion();
                    msg.push(`💎 JACKPOT WON +${data.jackpot_amount}`);
                } else if(data.reward >= 200){
                    safePlay($("jackpotSound"));
                    msg.push(`💥 BIG WIN +${data.reward}`);
                } else {
                    safePlay($("winSound"));
                    msg.push(`🎉 WIN +${data.reward}`);
                }

                highlightWinningLines(data.winning_lines || []);

                if(data.bonus_trigger && data.bonus_win > 0){
                    showBonusOverlay(data.bonus_win);
                }
            } else {
                msg.push("😈 NO WIN");
            }

            $("result").textContent = msg.join("  |  ");

            spinning = false;

            if(autoRemaining > 0){
                autoRemaining--;
                setTimeout(()=>spin(), 900);
            }
        }, 900);

    } catch(e){
        clearInterval(anim);
        $("result").textContent = "❌ Error";
        autoRemaining = 0;
        spinning = false;
    }
}

function startAuto(n){
    autoRemaining = n;
    spin();
}

function stopAuto(){
    autoRemaining = 0;
}

document.addEventListener("DOMContentLoaded", ()=>{
    setBet(1);

    $("spinBtn").addEventListener("click", spin);
    $("stopAutoBtn").addEventListener("click", stopAuto);

    document.querySelectorAll(".betbtn").forEach(btn=>{
        btn.addEventListener("click", ()=>setBet(Number(btn.dataset.bet)));
    });

    document.querySelectorAll(".autobtn").forEach(btn=>{
        btn.addEventListener("click", ()=>startAuto(Number(btn.dataset.auto)));
    });

    $("closeBonusBtn").addEventListener("click", hideBonusOverlay);
    document.querySelectorAll(".chestBtn").forEach(btn=>{
        btn.addEventListener("click", hideBonusOverlay);
    });

    renderGrid([
        ["❔","❔","❔","❔","❔"],
        ["❔","❔","❔","❔","❔"],
        ["❔","❔","❔","❔","❔"],
    ]);
});

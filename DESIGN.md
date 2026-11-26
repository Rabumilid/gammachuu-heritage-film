# Creative & Narrative Design (`DESIGN.md`)

## 1. Audience, Intent & Cultural Grounding (Defined Pre-Generation)

- **Intended Audience:**
  - **Primary Audience:** Ethiopian and Oromo family members, elders, and youth watching on smartphones (`9:16` vertical on Telegram, WhatsApp, TikTok, and YouTube Shorts), where authentic family stories narrated in Afaan Oromoo are rarely represented.
  - **Secondary Audience:** International peers and technical reviewers watching the widescreen `16:9` cut with English subtitles.
- **Core Emotional & Intellectual Intent:** When the film concludes, viewers should feel quiet pride, gratitude, and hope—understanding that self-discipline, literacy, and dignity in humble work can transform a family's trajectory across generations even when sudden illness forces a complete change of livelihood.
- **Material & Cultural Authenticity:** Every visual prompt is anchored in recognizable Oromo and Ethiopian highland life rather than generic Western defaults: handwoven white cotton *gabi* shawls, wooden *maresha* ox-plows, terraced highland farms, earthen-walled *gojo* homes, studying by brass kerosene lantern light, a wife in a colorful *tibeb*-bordered *netela* wrapping homemade *daabboo* bread, a modest town tea house (*mana shaayii*), and a vintage black cast-iron foot-pedal treadle sewing machine.

## 2. Three-Act Visual & Lighting Progression

| Act | Shots | Narrative Beat | Color & Lighting Palette | Wardrobe & Continuity Anchors |
| :--- | :--- | :--- | :--- | :--- |
| **Act I: Farm & Illness** | `shot_01` – `shot_04` | Gammachuu farms the highland soil, falls physically ill, and watches heavy rain fall outside his window. | Golden sunrise backlight → muted earthen interior shadows → cool overcast rain-blue light. | 38-year-old Oromo man, short black curly hair, neatly trimmed short beard, white handwoven *gabi* shawl. |
| **Act II: Literacy & Resolve** | `shot_05` – `shot_09` | Practices writing by lantern light, resolves at dawn to rebuild, travels to town with *daabboo* bread and tea. | Warm amber kerosene glow → bright morning doorway sunbeams → soft café window light. | White *gabi*; wife wears *tibeb*-bordered *netela*; cloth-wrapped *daabboo* bread and glass of spiced *shaayii*. |
| **Act III: Craft & Legacy** | `shot_10` – `shot_14` | Masters tailoring on a treadle machine, builds a town home, employs young tailors, and educates his children. | Warm directional workshop light → rich golden-hour sunlight on a paved town street. | Crisp light-blue collared shirt, yellow measuring tape, and tailored dark blazer in `shot_14`. |

## 3. Stated Narrative Reason for Every Shot (14 Shots)

Every shot in `storyboard.json` serves a distinct narrative beat and is composed inside the center 55% horizontal safe zone so `final_9x16.mp4` center-crops cleanly without clipping faces, hands, or props:

| Shot | Framing | Stated Reason in Story | Cultural Visual Anchors |
| :--- | :--- | :--- | :--- |
| `shot_01` | Wide establishing | Establishes Gammachuu's identity and strength as a rural highland farmer before illness interrupts his life. | Tilling dark highland soil with a traditional wooden *maresha* ox-plow and terraced hills at sunrise. |
| `shot_02` | Medium shot | Introduces the central conflict: sudden physical illness leaving him unable to perform heavy farm labor. | Seated on a carved wooden stool inside a rural earthen home wrapped in a white *gabi*, hand on chest. |
| `shot_03` | Medium close-up | Externalizes his uncertainty and isolation through heavy highland rain falling on the red soil outside. | Seated beside a rustic wooden shutter window watching rain fall on highland soil and banana plants. |
| `shot_04` | Close-up | Captures the internal emotional turning point—shifting from quiet grief to steady determination. | Tight portrait lit by soft cool window light; eyes placed on upper-center third for `9:16` framing. |
| `shot_05` | Close-up insert | Shows his first concrete action toward reinvention: teaching himself to write at night. | Hands writing with a ballpoint pen in a worn lined exercise book beside a glowing brass kerosene lantern. |
| `shot_06` | Medium close-up | Marks his decisive commitment at dawn to travel to town and learn a sustainable trade. | Standing in his open doorway as golden morning sunbeams break through rain clouds. |
| `shot_07` | Medium two-shot | Honors family solidarity and quiet sacrifice as his wife prepares provisions for his journey. | Wife in white *netela* with colorful *tibeb* border handing cloth-wrapped homemade *daabboo* bread at dawn. |
| `shot_08` | Medium shot | Depicts humility and frugality during his early apprenticeship days in town. | Sitting alone at a worn wooden table in a modest *mana shaayii* with a clear glass of hot spiced tea. |
| `shot_09` | Close-up insert | Reinforces self-reliance—eating his wife's homemade *daabboo* alongside a single glass of tea. | Hands breaking small pieces of *daabboo* next to steaming amber tea and a woven cloth shoulder bag. |
| `shot_10` | Medium shot | Demonstrates mastery of tailoring craft through focused, patient daily practice. | Leaning forward at a vintage black cast-iron treadle sewing machine stitching woven cotton fabric. |
| `shot_11` | Medium wide | Shows the first tangible reward of his perseverance: a stable town home and children in school. | Gammachuu and his wife smiling outside their plastered town house beside their school-bound children. |
| `shot_12` | Medium close-up | Contrasts directly with `shot_04`—showing his transformed confidence as a respected shop owner. | Crisp light-blue collared shirt inside a bright tailoring shop lined with colorful fabric bolts. |
| `shot_13` | Wide shot | Illustrates community uplift as his workshop grows to train and employ two young tailors. | Bustling town tailoring shop (*suuqii*) with garment racks and two young tailors at sewing machines. |
| `shot_14` | Wide hero shot | Delivers the intergenerational payoff: a successful businessman standing proudly with his educated children. | Tailored dark blazer outside his thriving town storefront in golden-hour sun flanked by his grown son and daughter. |

## 4. User Testing & Iterative Storyboard Revisions

### User Test 1 — Radio Cut Prototype (Audio + Storyboard Timing)

- **Artifact Tested:** 14-segment Afaan Oromoo narration track (`44.1 kHz` mono) sequenced over placeholder underscore against a black timing slate (`~84s` narration + `3.0s` end card).
- **Participants (3 target audience members):**
  - **Tester 1 (Family Elder, native Afaan Oromoo speaker):** Evaluated cultural resonance, emotional pacing, and pronunciation of names and cultural nouns.
  - **Tester 2 (Oromo University Peer, Addis Ababa):** Evaluated speech clarity on smartphone speakers and English subtitle readability.
  - **Tester 3 (Cohort Colleague):** Evaluated 3-act narrative clarity from audio and subtitles alone before visual rendering.
- **What They Said & What Changed in `storyboard.json`:**
  - **Act Transition Breathing Space:** Tester 1 noted that moving immediately from illness (`shot_04`) into night writing (`shot_05`) felt hurried. Added `0.4s` of room-tone padding at the end of `shot_04` and `shot_09` so emotional pivots land cleanly.
  - **Cultural Lexicon & Phrasing:** Tester 1 confirmed accurate pronunciation of *Gammachuu*, *daabboo*, and *shaayii*, and suggested warmer phrasing in `shot_07` to emphasize his wife's encouragement.
  - **Mobile Subtitle Line Length:** Tester 2 observed that English subtitles longer than ~42 characters wrapped onto three lines on narrow phone screens. Tightened all 14 `subtitle_en` entries in `storyboard.json` to at most two lines (`<= 38` chars/line).

### User Test 2 — Near-Final Cut (`final_9x16.mp4` & `final_16x9.mp4`)

- **Artifact Tested:** Assembled dual-aspect film combining Cloudflare `FLUX.2` keyframes, Kaggle `Wan 2.2` hero clips, suppressed D-minor chamber classical score, burned-in English subtitles, and `3.0s` AI disclosure card.
- **Participants (3 target audience members):**
  - **Tester 1 (Family Elder):** Reviewed `final_9x16.mp4` on an Android smartphone.
  - **Tester 2 (Oromo Peer):** Reviewed `final_9x16.mp4` on mobile earbuds and phone speaker.
  - **Tester 3 (Cohort Colleague):** Reviewed `final_16x9.mp4` on a laptop display.
- **What They Said & What Changed in `storyboard.json` & `pipeline/`:**
  - **Clearer Agricultural Action in `shot_01`:** Tester 1 noted that the initial draft of `shot_01` (walking along a path) did not immediately communicate farm labor. Updated `shot_01` (`seed=1101`) to depict active tilling with a traditional Ethiopian wooden *maresha* ox-plow and terraced highland fields.
  - **Age Continuity Fix in `shot_02`:** Tester 3 pointed out that Gammachuu appeared much older in `shot_02` than in `shot_01` and `shot_04`. Removed the age-biasing word `"exhausted"` and added `shot_02` (`seed=1102`) to `PORTRAIT_CONDITIONED_SHOTS` in `pipeline/keyframes.py`.
  - **Stronger Town Businessman Finale (`shot_14`) & Suppressed Score:** Tester 1 requested a clearer visual payoff of his business success in town, leading to `shot_14` (`seed=1114`) outside his thriving town storefront. Tester 2 confirmed that the `-5 dB` EQ dip at `1.8 kHz` and `8:1` sidechain ducking kept every Afaan Oromoo word crisp over the cello and felt piano score.

# Consent Record, Licensing & AI Disclosure (`ETHICS.md`)

## 1. Informed Consent Record (Mandatory Gate Verification)

- **Subject & Family Provenance:** This short film dramatizes the lived family history of Gammachuu, an Ethiopian Oromo farmer who overcame illness through literacy and tailoring.
- **Recorded Family Story Consent:** Prior to drafting the script or generating any media, informed verbal and written consent was obtained from family elders/storytellers (recorded on November 24, 2026) authorizing the telling of Gammachuu's story in Afaan Oromoo for public educational and portfolio showcase.
- **Strict Non-Biometric & Non-Cloned Safeguards:**
  - **Zero Real Faces Uploaded:** No photograph, video, or biometric facial scan of Gammachuu or any living relative was uploaded to any AI model. Every character in the film is a synthetic visual composite generated purely from cultural text descriptions.
  - **Zero Cloned Voices Used:** No real person's voice was recorded for voice cloning. Narration was synthesized using a standard non-cloned Afaan Oromoo TTS voice via Addis AI reading the author's original script.

## 2. Model & Output Licenses

| Component / Model | Provider / Source | License | Usage & Distribution Terms |
| :--- | :--- | :--- | :--- |
| `Wan 2.2` (`Wan2.2-TI2V-5B`) | Wan-AI (`huggingface.co/Wan-AI/Wan2.2-TI2V-5B-Diffusers`) | Apache License 2.0 | Permissive open weights; allows modification, distribution, and commercial/non-commercial use with attribution. |
| `FLUX.2 [klein] 4B` & `FLUX.1 [schnell]` | Black Forest Labs via Cloudflare Workers AI | Apache License 2.0 | Permissive open-weight distilled models; executed via Cloudflare Workers AI REST API. |
| **Addis AI TTS** | Addis AI (`api.addisassistant.com`) | Proprietary API Terms | Author retains full rights to original Afaan Oromoo script and synthesized narration audio for showcase and distribution. |
| **Chamber Classical Underscore** | Original Python/NumPy DSP synthesis (`pipeline/`) | MIT / Public Domain | Original algorithmic synthesis authored in this repository; cleared for unrestricted distribution. |
| **FFmpeg** | FFmpeg Project | LGPL v2.1+ / GPL v2+ | External CLI tool used for deterministic audio/video assembly and `-14 LUFS` mastering. |

## 3. Labelling & Privacy Plan

- **Mandatory 3.0-Second AI End Card:** Both `outputs/video/final_9x16.mp4` and `outputs/video/final_16x9.mp4` conclude with a high-contrast 3.0-second end card stating: `"Created with AI: Afaan Oromoo narration (Addis AI), visuals (FLUX.2 & Wan 2.2), and score (original chamber synthesis) from a family story."`
- **Platform AI Disclosure Label:** When publishing on social media, the platform's native **"AI-generated / Made with AI"** content disclosure toggle is switched **On**, and all AI tools are credited in the post text.
- **Privacy Protection:** No national IDs, exact residential coordinates, medical records, or private family phone numbers were sent to external APIs.

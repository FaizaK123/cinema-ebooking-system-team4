/* Frontend-only promotion form preview. */
const promotionForm = document.getElementById("promotion-form");

if (promotionForm) {
    const promotionMessage = document.getElementById("promotion-form-message");
    const campaignList = document.getElementById("promotion-campaigns-list");
    const startDate = document.getElementById("promotion-start-date");
    const endDate = document.getElementById("promotion-end-date");
    const promotionPreviews = [];

    function setPromotionMessage(message, type) {
        promotionMessage.textContent = message;
        promotionMessage.classList.toggle("is-error", type === "error");
        promotionMessage.classList.toggle("is-success", type === "success");
    }

    function createCampaignDetail(label, value) {
        const detail = document.createElement("span");
        detail.className = "promotion-campaign-detail";
        const heading = document.createElement("strong");
        heading.textContent = label;
        const text = document.createElement("span");
        text.textContent = value;
        detail.append(heading, text);
        return detail;
    }

    function renderPreviews() {
        campaignList.replaceChildren();
        if (!promotionPreviews.length) {
            const empty = document.createElement("p");
            empty.className = "promotion-campaigns-empty";
            empty.textContent = "Promotion previews will appear here.";
            campaignList.append(empty);
            return;
        }

        promotionPreviews.forEach((promotion) => {
            const card = document.createElement("article");
            card.className = "promotion-campaign-card";
            const heading = document.createElement("h3");
            heading.textContent = `${promotion.promoCode} - ${promotion.discountPercent}% off`;
            const description = document.createElement("p");
            description.className = "promotion-campaign-description";
            description.textContent = promotion.description;
            const details = document.createElement("div");
            details.className = "promotion-campaign-details";
            details.append(
                createCampaignDetail("Email subject", promotion.emailSubject),
                createCampaignDetail("Valid", `${promotion.startDate} to ${promotion.endDate}`),
                createCampaignDetail("Target audience", "Would target subscribed users (not connected)"),
                createCampaignDetail("Email status", "Preview only - not saved or sent"),
                createCampaignDetail("Email message", promotion.emailBody)
            );
            card.append(heading, description, details);
            campaignList.append(card);
        });
    }

    const today = new Date();
    startDate.min = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, "0"),
        String(today.getDate()).padStart(2, "0")
    ].join("-");
    endDate.min = startDate.min;
    startDate.addEventListener("change", () => {
        endDate.min = startDate.value || startDate.min;
        if (endDate.value && endDate.value < startDate.value) endDate.value = startDate.value;
    });

    promotionForm.addEventListener("submit", (event) => {
        event.preventDefault();
        if (!promotionForm.reportValidity()) return;

        const formData = new FormData(promotionForm);
        const promotion = {
            promoCode: formData.get("promoCode").trim().toUpperCase(),
            description: formData.get("description").trim(),
            discountPercent: formData.get("discountPercent"),
            startDate: formData.get("startDate"),
            endDate: formData.get("endDate"),
            emailSubject: formData.get("emailSubject").trim(),
            emailBody: formData.get("emailBody").trim()
        };

        if (promotionPreviews.some((preview) => preview.promoCode === promotion.promoCode)) {
            setPromotionMessage("That promotion code is already in this preview.", "error");
            return;
        }

        promotionPreviews.unshift(promotion);
        renderPreviews();
        promotionForm.reset();
        endDate.min = startDate.min;
        setPromotionMessage("Preview created in this page only. Nothing was saved or emailed.", "success");
    });

    renderPreviews();
}

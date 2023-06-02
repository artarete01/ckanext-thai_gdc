ckan.module('gdc_agency_hint_view', ($) => {
    return {
        createIcon: () => {
            const icon = document.createElement('span');
            icon.innerHTML = '<span class="fa fa-info"></span>';
            icon.classList.add('gdc-field-hint-icon');
            return icon;
        },
        createTooltip: des => {
            const tip = document.createElement('div');
            const txt = des.replace(/\n/g, "<br/>");
            tip.innerHTML = txt;
            tip.classList.add('gdc-field-hint-tooltip');
            return tip
        },
        removeTooltipActive: current => {
            document.querySelectorAll(".gdc-field-hint-tooltip.active").forEach(tip => {
                if (tip !== current) tip.classList.remove('active')
            });
        },
        initialize: async function () {

            document.addEventListener('click', () => {
                this.removeTooltipActive(null);
            });

            try {
                const raw = await fetch(this.options.des_url);
                const res = await raw.json();
                const metaCategory = this.options.hasOwnProperty('cat') && res.hasOwnProperty(this.options.cat) ? this.options.cat : 'metadata';
                const meta = res[metaCategory];
                for (const field in meta) {
                    const labelObj = document.getElementById(field)
                    const des = meta[field]['des']

                    if (!labelObj || typeof des === undefined) continue;

                    const icWrap = document.createElement('span');
                    icWrap.style.position = 'relative';
                    icWrap.style.display = 'inline-block';
                    labelObj.appendChild(icWrap);

                    const icon = this.createIcon();
                    icWrap.appendChild(icon);

                    const tip = this.createTooltip(des);
                    icWrap.appendChild(tip);


                    icon.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        this.removeTooltipActive(tip);

                        const clientWidth = document.body.clientWidth;
                        if (clientWidth < 580) {
                            tip.style.top = `${icon.offsetTop + 30}px`;
                            tip.style.left = `${icon.offsetLeft - 30}px`;
                        } else {
                            tip.style.top = `${icon.offsetTop - 10}px`;
                            tip.style.left = `${icon.offsetLeft + 30}px`;
                        }

                        tip.classList.toggle('active')
                    });

                    tip.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                    });

                }


            } catch (e) {
            }
        }
    }
});
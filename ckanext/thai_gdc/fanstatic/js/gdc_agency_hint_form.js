ckan.module('gdc_agency_hint_form', ($) => {
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

            document.querySelector('.dataset-form').addEventListener('submit', (e) => {
                const maintainerEmailValue = document.getElementById('field-maintainer_email').value;

                if (maintainerEmailValue !== '') {
                    const valid = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/.test(maintainerEmailValue)
                    if (!valid) {
                        alert('อีเมลไม่ถูกต้อง');
                        e.preventDefault();
                        document.getElementById('field-maintainer_email').focus();

                        setTimeout(() => {
                            document.querySelector('.form-actions button[type=submit]').removeAttribute('disabled');
                        }, 1000);
                    }
                }
            });

             try {
                 document.getElementById('s2id_field-tag_string').classList.remove('form-control');
             }catch (e) {
                 
             }

            try {
                const raw = await fetch(this.options.des_url);
                const res = await raw.json();
                const metaCategory = this.options.hasOwnProperty('cat') && res.hasOwnProperty(this.options.cat) ? this.options.cat : 'metadata';
                const meta = res[metaCategory];
                for (const field in meta) {

                    let fieldId = field;
                    if (field === 'field-objective') fieldId = 'field-objective-ยุทธศาสตร์ชาติ';
                    if (field === 'field-data_format') fieldId = 'field-data_format-Database';
                    if (field === 'field-data_language') fieldId = 'field-data_language-ไทย';
                    if (field === 'field-disaggregate') fieldId = 'field-disaggregate-ไม่มี';

                    const labelObj = $(`#${fieldId}`)
                    const des = meta[field]['des']

                    if (!labelObj || typeof des === undefined) continue;


                    const icWrap = document.createElement('span');
                    icWrap.style.position = 'relative';
                    labelObj.closest('div.controls').siblings('label.control-label').append(icWrap);

                    const icon = this.createIcon();
                    icWrap.appendChild(icon);

                    const tip = this.createTooltip(des);
                    icWrap.appendChild(tip);


                    icon.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        this.removeTooltipActive(tip);
                        tip.style.top = `${icon.offsetTop - 10}px`;
                        tip.style.left = `${icon.offsetLeft + 30}px`;
                        tip.classList.toggle('active')
                    });

                    tip.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                    });

                    if (field === 'field-name' && document.getElementById('field-title')){
                        document.getElementById('field-title').nextSibling.append(icWrap);
                    }

                }


            } catch (e) {
                console.log(e);
            }
        }
    }
});

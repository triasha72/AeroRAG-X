# Claim-support review batch 02

Allowed labels: `SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`.

---

## claimrev_016

**Systems:** base_rag

**Claim:** Aerothermal Shape Optimization of Actively-Cooled Battery Packs using Conjugate Heat Transfer Ping He, Christian Psenica, and Lean Fang

**Cited evidence:**

- `C1` | `20240014672:chunk:00000`

Aerothermal Shape Optimization of Actively-Cooled Battery Packs using Conjugate Heat Transfer Ping He∗, Christian A. Psenica†, and Lean Fang‡ Iowa State University, Ames, IA 50011 Mark K. Leader§ NASA Glenn Research Center, Cleveland, OH 44135 Thermal management for batteries is important for electric aircraft because battery temperature is critically important to vehicle safety, and it also has a direct impact on the efficiency of the battery system. Because ambient air is a readily available resource for aircraft, this paper considers an active cooling concept with forced convection of ambient air through the battery pack. Conjugate heat transfer analysis is used to solve the coupled aero-thermal problem, which consists of a finite-volume computational fluid dynamics solver for the fluid domain, and a conduction heat transfer solver for the solid domain. A mixed Neumann and Dirichlet boundary condition is developed for the fluid-solid interface, which allows the solid domain to completely submerge in the fluid domain. A gradient-based optimization method is adopted, and the discrete adjoint approach implemented in DAFoam is used to efficiently compute the gradients. The aero-thermal coupling for primal analysis and gradient computation is handled using the OpenMDAO-based MPhys framework. A constant heat source is prescribed for the battery cells, and the battery shape (design variable) is optimized to minimize cooling pump power and battery weight (composite objective function) while keeping the battery temperature below a threshold (constraint). The optimized design achieves a 44.6% and 1.5% reduction in the cooling pump power and battery weight, respectively, and the maximal temperature constraint is satisfied. This work has the potential to reduce battery-pack weight, improve performance, and reduce the weight of thermal management systems for electric vertical take-off and landing aircraft. I. Introduction Thermal management is essential for battery packs in electric aircraft, which lack the natural heat dissipation of conventional

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_017

**Systems:** lora_rag

**Claim:** Conjugate heat transfer (CHT) optimization is used to analyze the aerodynamics and heat transfer of battery pack shapes and flow conditions, enabling more realistic aero-thermal coupling.

**Cited evidence:**

- `C1` | `20240014672:chunk:00000`

Aerothermal Shape Optimization of Actively-Cooled Battery Packs using Conjugate Heat Transfer Ping He∗, Christian A. Psenica†, and Lean Fang‡ Iowa State University, Ames, IA 50011 Mark K. Leader§ NASA Glenn Research Center, Cleveland, OH 44135 Thermal management for batteries is important for electric aircraft because battery temperature is critically important to vehicle safety, and it also has a direct impact on the efficiency of the battery system. Because ambient air is a readily available resource for aircraft, this paper considers an active cooling concept with forced convection of ambient air through the battery pack. Conjugate heat transfer analysis is used to solve the coupled aero-thermal problem, which consists of a finite-volume computational fluid dynamics solver for the fluid domain, and a conduction heat transfer solver for the solid domain. A mixed Neumann and Dirichlet boundary condition is developed for the fluid-solid interface, which allows the solid domain to completely submerge in the fluid domain. A gradient-based optimization method is adopted, and the discrete adjoint approach implemented in DAFoam is used to efficiently compute the gradients. The aero-thermal coupling for primal analysis and gradient computation is handled using the OpenMDAO-based MPhys framework. A constant heat source is prescribed for the battery cells, and the battery shape (design variable) is optimized to minimize cooling pump power and battery weight (composite objective function) while keeping the battery temperature below a threshold (constraint). The optimized design achieves a 44.6% and 1.5% reduction in the cooling pump power and battery weight, respectively, and the maximal temperature constraint is satisfied. This work has the potential to reduce battery-pack weight, improve performance, and reduce the weight of thermal management systems for electric vertical take-off and landing aircraft. I. Introduction Thermal management is essential for battery packs in electric aircraft, which lack the natural heat dissipation of conventional

- `C2` | `20240014672:chunk:00001`

cooling pump power and battery weight, respectively, and the maximal temperature constraint is satisfied. This work has the potential to reduce battery-pack weight, improve performance, and reduce the weight of thermal management systems for electric vertical take-off and landing aircraft. I. Introduction Thermal management is essential for battery packs in electric aircraft, which lack the natural heat dissipation of conventional air-breathing engines [1]. Accumulated heat can damage batteries and other components, compromising the safety and performance of the aircraft. There are two primary methods for cooling the battery: passive and active. Passive cooling has the advantage of not requiring additional pumps or power, but it typically requires a greater surface area dedicated to heat rejection to the external environment, thereby increasing the overall weight of the battery pack. In contrast, active cooling can significantly reduce the battery pack weight, but it requires an efficient cooling system design to offset the added weight and power of the cooling pump [2]. Because ambient air is a readily available resource for aircraft, this paper considers an active cooling concept with forced convection of ambient air through the battery pack. Conjugate heat transfer (CHT) optimization is a powerful approach to designing high-performance active cooling battery packs. It enables more realistic aero-thermal coupling by integrating computational fluid dynamics (CFD) to simulate fluid domains and conduction heat transfer solvers for the solid domains. The CHT optimization method has been used to analyze the aerodynamics and heat transfer of various battery pack shapes and flow conditions [3, 4]. CHT-based design optimization studies have also been conducted to improve ∗Assistant Professor, Department of Aerospace Engineering, AIAA Senior Member. Email: phe@iastate.edu †PhD Student, Department of Aerospace Engineering, AIAA Student Member. ‡PhD Student, Department of Aerospace Engineering, AIAA Student Member. §Research Engineer, Propulsion Systems Analysis Branch, AIAA Member. 1 performance[5];however,inthisstudy,agradient-freeoptimizationalgorithmwasused.

- `C3` | `20260000381:chunk:00001`

a 3-by-3 cell configuration is cooled by ambient airflow, with constant heat generation prescribed in the cells. The battery casing shape serves as the design variable, and the objective function is a weighted sum of pressure loss and pack weight, subject to a maximum temperature constraint. The optimized design achieves a 44.6% reduction in pressure loss and a 1.5% reduction in weight, while satisfying the thermal constraint. To ensure the reliability of the optimized designs, this study validates coarse-mesh, steady-state predictions against fine-mesh unsteady simulations, demonstrating consistency within accept- able errors. This work demonstrates the potential of the developed framework to enable rapid, high-fidelity design of thermal management systems for electric aircraft. Keywords: Conjugate Heat Transfer; Design Optimization; Discrete Adjoint; eVTOL Thermal Management ∗Corresponding author Email address: phe@iastate.edu (Ping He) Preprint accepted for publication in International Journal of Heat and Mass Transfer January 7, 2026 Nomenclature1 Symbols2 CP L Pressure loss coefficient Cp Specific heat at constant pressure f Objective function H Influence from neighboring cell velocities and source term N Number of nodes in interpolation Q Heat flux; volumetric flow rate R Residual vector Sf Face area vector w State variable vector W Battery weight ∆T Temperature difference κ Thermal conductivity µ Dynamic viscosity; mesh skewness parameter ϕ Face flux; heat flux Ψ Adjoint variable vector Subscripts and Superscripts3 (·)fluid Fluid domain quantity (·)solid Solid domain quantity (·)f Face quantity (·)N Neighboring cell quantity (·)P Control volume cell quantity (·)ref Reference value (·)w Wall quantity Acronyms and Abbreviations4 BC Boundary Condition CFD Computational Fluid Dynamics CHT Conjugate Heat Transfer FFD Free-Form Deformation XDSM Extended Design Structure Matrix 2 1. Introduction5 Effective thermal management is a critical design challenge in electric aircraft, which lack the natural6 heat dissipation mechanisms found in conventional air-breathing engines [1]. Excessive heat buildup can7 compromise

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_018

**Systems:** lora_rag

**Claim:** Hybrid-electric propulsion hazards include fuel system ignition from direct lightning strikes, corona or streamer at fuel vent outlets, and the hazards introduced by a hybrid power system.

**Cited evidence:**

- `C1` | `20190033416:chunk:00018`

But many FUELEAP stakeholders —systems engineers, electrical and avionics engineers, pilots, safety specialists, and regulators—will be unfamiliar with both the safety and operational concerns surrounding hybrid electric propulsion and the relative merits of means of addressing these. Such stakeholders might benefit from a guide to how power system des ign fit into in the ‘big picture’ of aircraft safety. One way the safety argument augments our modeling and safety assessment activities is by explaining that story to readers. Fig. 4 The top-level of the FUELEAP safety argument in the Goal Structuring Notation (Ref 15) When means of addressing aircraft hazards or assessing aircraft safety are familiar, it may not be necessary to explain these to readers beyond, perhaps, referencing applicable standards. Safety-related standards and regulations often serve to define best practice, capturing judgments about which hazards require mitigation and sometimes what mitigations are advisable and how they should be assessed. But these judgments might not be universally applicable. For example, 14CFR §23.2430.a.2 requires that aircraft fuel systems be “designed and arranged to prevent ignition of the fuel within the system by direct lightning strikes … or by corona or streamering at fuel vent outlets,” thus implicitly presuming both a liquid fossil fuel energy source and an attendant fire hazard. But it makes no mention of the hazards introduced by the use of a battery pack of the construction and capacity required by a hybrid power 9 system. By capturing the hazards that FUELEAP’s project team envision and relating these hazards to mitigations, the safety argument records the team’s contention as to which unique hazards require mitigation and what means of mitigation should be considered sufficient. The argument will thus serve as the starting poi nt for discussing these matters with relevant regulators, including the NASA ASRB. FUELEAP’s nature as a

- `C2` | `20170006610:chunk:00000`

1 American Institute of Aeronautics and Astronautics A NASA Approach to Safety Considerations for Electric Propulsion Aircraft Testbeds Kurt V. Papathakis1 and Alaric M. Sessions2 NASA Armstrong Flight Research Center, Edwards, CA, 93523 Phillip A. Burkhardt3 and David W. Ehmann4 Jacobs Technology, Edwards, CA, 93523 Electric, hybrid -electric, and turbo -electric distributed propulsion technologies and concepts are beginning to gain traction in the aircraft design community, as they can provide improvements in operating costs, noise, fuel consumption, and emissions compared to conventional internal combustion or B rayton-cycle powered vehicles. The National Aeronautics and Space Administration ( NASA) is building multiple demonstrators and testbeds to buy down airworthiness and flight safety risks for these new technologies, including X-57 Maxwell, Hybrid-Electric Integrated Systems Testbed (HEIST), Airvolt, and NASA Electric Aircraft Testbed (NEAT). This paper addresses the safety system design process used at NASA Armstrong Flight Research Center, speci fic ha zards associated with these new electric propulsion technologies, including an extensive investigation into the emergency -stop system for a HEIST, and other best practices. In general, the best course of action is to actively design out hazards assoc iated with these systems, but when removing these hazards is either impossible or impractical, other safety protocols including keep -out zones, lock -out/tag-out, and other practices should be implemented. Nomenclature A = amperage AC = alternating current AC/DC = alternating current to direct current (converter) AFRC = Armstrong Flight Research Center AFSRB = airworthiness and flight safety review board ARMD = Aeronautics Research Mission Directorate BMS = battery management system CANBus = controller area network bus Cat = category CIS = cockpit interface system CRM = continuous risk management CST = combined systems test E-stop = emergency stop EMI = electromagnetic interference FMEA = failure modes and effects analysis HAM = hazard action matrix

- `C3` | `20170006610:chunk:00004`

at NASA AFRC neces sitated a testbed trailer setup, and allowed for testing flexibility while maintaining connectivity to the simulation laboratory.3 Airvolt was the first AFRC all-electric demonstration project, designed to be a fully-instrumented, single propulsor test stand in order to better understand and analyze how current from the batteries ultimately produced thrust from the propeller, via the bus architecture, motor controllers, motor, and other equipment. Airvolt is currently being used as a method of acceptance testing for the X-57 Maxwell JM-X57 cruise motors. NASA is aggressively pursuing multipl e all-electric, hybrid-electric, and turbo -electric models, test stands, and flying demonstrators, while endeavoring to maintain high levels of safety throughout the design process and testing. In order for these systems to retire electric, hybrid-electric, and turbo-electric distributed propulsion architecture risks, numerous safety considerations must be implemented, as these system s require high voltage and current, especially for the new megawatt-scale systems being proposed. A safety design is the inco rporation of control methods and processes which begins early in the system design to either eliminate a hazard or mitigate risks to human health and safety throughout the lifespan of the platform. II. Electric, Hybrid-Electric, and Turbo-Electric Testbed Hazards and Mitigations To help assure mission success for these all -electric, hybrid -electric, and turbo -electric distributed propulsion projects, NASA is leveraging the hazard analysis process from the NASA Hazard Management Procedure4 to identify, eliminate, or control to an acceptable level the hazards associated with the projects that could affect human safety, damage or loss of assets, or loss of mission during the conduct of operations. NASA AFRC has a stringent hazard identification and mitigation system allowing the Center to self-certify experimental aircraft. This process starts with identifying hazards in preliminary hazard reports, complete with causes, effects, mitigations, and then categorizes the

- `C4` | `20190033416:chunk:00019`

hazards that FUELEAP’s project team envision and relating these hazards to mitigations, the safety argument records the team’s contention as to which unique hazards require mitigation and what means of mitigation should be considered sufficient. The argument will thus serve as the starting poi nt for discussing these matters with relevant regulators, including the NASA ASRB. FUELEAP’s nature as a demonstrator project also poses challenges such as assessing the adequacy of operational constraints and tracking different short-term and long-term safety aims. The project’s goal is to assess the viability of the hybrid power system concept, not to develop an aircraft type that can be put into production. The power system concept is not viable if it will not be possible to (with further development) implement a sufficiently safe production version. Yet an aircraft built to assess a novel concept must, by nature, fly in order to accumulate the very experience that will provide a sound basis for assessing the reliability and other safety properties of the concept in question. Thus, adequate safety in flight test operations might be best achieved with a different set of mitigations than might be prudent in a production aircraft. For example, flight test operations might be conducted solely from runways long enough to permit landing straight ahead should the power system fail during takeoff. These considerations yield the safety aims embodied in the claims shown at the bottom of Fig. 9. In the argument supporting GDOCAAHEs —not shown here —we trace hazards in t he flight demonstrator aircraft to their mitigations and the related evidence to allow readers to understand how we have addressed the safety of flight test operations and to judge whether we have done so as well as reasonably practicable. At the same time, we must meet existing regulations for flight test.

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_019

**Systems:** lora_rag

**Claim:** Cryogenic tanks and their associated manufacturing, insulation, and integration into airframes are challenging due to the lower cryogenic fuel density requiring larger tanks for equivalent field length metrics.

**Cited evidence:**

- `C1` | `20250010867:chunk:00003`

methods for ignition sources, ﬂame propagation, and deﬂagration risks diﬀer signiﬁcantly across applications. Other subjects that need to be addressed in combination with the above regulatory challenges are the development of an encompassing aircraft architecture and optimal system integration making the commercial exploitation of a novel aircraft concept viable, as well as the development of relevant safety regulations and certiﬁcation standards for the aircraft and its major components [8]. These studies are focusing on hydrogen turbine engines, fuel cells, electric motors, and hybrid-electric cycles integrated with cryo-fuels using consistent metrics of aircraft eﬃciency and emission improvements. It is important to mature the technologies required in parallel to the aircraft architectures so that the two can feed each other improving the probability of integrated system success. There are numerous technology challenges for aviation with cryogenic fuel storage systems and propulsion including development of cryo-fuel storage and handling, thermal management systems, cryogenic fuel combustion in turbine engines, and next generation scalable engines and fuel cells. Initial challenge includes variabilities in turbine engines and fuel cells considered for integration into commercial aviation propulsion, each with expansive unknowns [9]. Cryogenic tank design, manufacturing, insulation, and integration into airframes will be challenging because of the lower density of the fuel requiring larger tanks for equivalent ﬁeld length metrics [8]. Liquid cryogenic fuels’ maximum handling maximum temperature and density signiﬁcantly diverge from baseline Jet A fuel (kerosene) at 182 °C and 807 kg/m3 with LNH 3 at -36.3 °C and 675 kg/m3, LNG at -160 °C and 424 kg/m3, and LH2 at -253 °C and 71 kg/m3. Although hydrogen oﬀers a much higher gravimetric energy density (LHV ≈ 120 MJ/kg) than jet fuel (LHV ≈ 43 MJ/kg), its low volumetric density requires bulky storage systems, posing substantial integration challenges for long-range, large aircraft. LH2 low temperature,

- `C2` | `20250010867:chunk:00004`

at -36.3 °C and 675 kg/m3, LNG at -160 °C and 424 kg/m3, and LH2 at -253 °C and 71 kg/m3. Although hydrogen oﬀers a much higher gravimetric energy density (LHV ≈ 120 MJ/kg) than jet fuel (LHV ≈ 43 MJ/kg), its low volumetric density requires bulky storage systems, posing substantial integration challenges for long-range, large aircraft. LH2 low temperature, low density, low viscosity, low lubricity, small molecular size (harder to control leakage), wide ﬂammability range (between 4% and 75% in air), and potential for diﬀusion into or reaction with other materials increases the challenge of the design of systems that can simultaneously accommodate all these characteristics for a long (and highly cyclic) design life, in a lightweight, volumetrically eﬃcient form factor. While many of these attributes have been successfully dealt with in ground systems, where weight is not a primary driver, or in space ﬂight systems, where cryogenic systems are typically designed for short life (< 1 hour) and a low number of thermal and pressure cycles, there are several identiﬁed technology gaps with respect to the speciﬁc characteristics needed in an aviation application, including the requirement of suﬃcient durability for thousands of cycles and hours. Similar to the cryogenic systems, the state-of-the-art fuel cell technology is validated for automotive applications and is too heavy for aeronautics. Fuel cells for space applications operate on pure oxygen rather than air, are at low scale, and designed to operate over a limited number of cycles. The fuel cell technology for aeronautical applications requires extensive technology maturation and scale up that achieves high speciﬁc energy at the system level and will require signiﬁcant long-term investments to develop the technology and integrate it into cryogenic fuel aircraft architecture. Fuel cell material durability and performance under variable loads and operational stresses (e.g., takeoﬀ-shutdown cycling,

- `C3` | `20250010867:chunk:00002`

from commercial airports rather than isolated launch sites. Aviation systems will be required to safely operate in occupied vehicles that are used several times a day, yet not dissembled and manually inspected between each ﬂight. Safety and certiﬁcation requirements for airframes with large integrated cryogenic tanks need to be deﬁned in partnership with the Federal Aviation Administration (FAA) to increase the likelihood of passenger survival in the event of a crash. Systems for detecting and mitigating fuel leakage would have to be automated and redundant beyond current baseline operational procedures for space systems. Mean times between failure (MTBF) suitable for practical aviation propulsion life cycles will have to be demonstrated through actual testing of brassboard and production systems, and they will be required to meet FAA safety and certiﬁcation requirements no less stringent than those for current commercial aircraft. Safety standards for hydrogen systems remain fragmented and inconsistent across regions. High-pressure storage, such as 350- and 700-bar systems, is governed by varying standards (ISO, SAE, EU) that are not fully harmonized, creating interoperability challenges. Similarly, leak detection and mitigation are hindered by the lack of uniﬁed, validated performance standards for hydrogen sensors in diverse environments, including outdoor refueling stations and industrial facilities. Material compatibility also remains a concern, as current qualiﬁcation standards do not comprehensively address low temperature embrittlement or hydrogen embrittlement in metals or degradation in composite materials. Fire and explosion protection adds another layer of complexity, since testing methods for ignition sources, ﬂame propagation, and deﬂagration risks diﬀer signiﬁcantly across applications. Other subjects that need to be addressed in combination with the above regulatory challenges are the development of an encompassing aircraft architecture and optimal system integration making the commercial exploitation of a novel aircraft concept viable, as well as the development of relevant safety regulations and certiﬁcation

- `C4` | `20260003867:chunk:00000`

Cryogenic Fuel Aviation – Challenges and Opportunities Vadim F. Lvovich, Wesley L. Johnson, Ian J. Jakupca, H. Douglas Perkins, Thomas M. Lavelle, Hashmatullah Hasseeb, Ezra O. McNichols, F. David Koci, Sandi G. Miller, Stephanie L. Vivod, Sadeq Malakooti, Joseph J. Pinakidis, Zhimin Zhong, Brett A. Bednarcyk, Evan J. Pineda, Brandon L. Hearley, Rula M. Coroneos, Joshua Stuckner NASA Glenn Research Center, Cleveland, Ohio Christopher L. Hartman Analytical Mechanics Associates, Hampton, Virginia Mahtab Fox HX5 LLC, Cleveland, Ohio June 10, 2026 AIAA 2026 Aviation Forum, San Diego, CA NASA Technology Development Focus in Aeronautics Fuel Production Fuel Transportation Airport Infrastructure - Ground Handling - Refueling Aircraft Overall Environmental Impact -Initial investment -Fuel cost/availability -Carbon Tax?, etc. -Nation, global energy policies Multiple Fuel Types? • Primary focus will be the aircraft • Single-aisle and larger is the ultimate long-term interest • Experience with smaller applications should be leveraged • Any propulsion systems using cryogenic fuels were within scope (gas-turbine, fuel cells, hybrid) Less focus will be devoted to non-aircraft considerations Not a direct part of NASA Scope External Perspective on NASA Research Investment Opportunities Results from September 2022 “Cryogenic Fuel Systems for Aircraft” Workshop at GRC • Materials • Additive manufacturing and composites for cryo temperatures, cycle fatigue, and hydrogen permeation • Seals, insulation, embrittlement, thermal expansion • Structures • Fuel tank, pressurized structure, conformal pressure vessels, impact absorbing structures • Testing Capabilities and Techniques • Hydrogen enabled facilities, crashworthiness, impact testing, icing • Operations • ConOps development, fuel system purging, fueling/defueling operations, tarmac hold, failure analysis, contingency scenarios unique to cryogenics • Systems Studies • Concept studies, fuel cell vs hydrogen combustion vs combination, fuel cell as secondary power (APU replacement), impact of current vs future grid, exploration of acceptable boil-off, tank design trades • Propulsion and Powertrain • Combustor design

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_020

**Systems:** base_rag

**Claim:** The transition from LT PEM to HT PEM is necessary to achieve large temperature differential between coolant and airstream during takeoff and climb.

**Cited evidence:**

- `C1` | `20260003867:chunk:00010`

approaches for MW fuel cell stacks – Lightweight BOP , water and thermal management • Systems Analysis to assess new vehicle configurations Thermal Management System Considerations • Need to reject 40% to 60% of the fuel cell heat energy (~10 MWt) • Need to transition from LT PEM (80C) to HT PEM (200C) to achieve large temperature differential between coolant and airstream during takeoff and climb • Heat rejection must close at zero flight speed, necessitating the placement of the heat exchanger in the propulsor duct • At takeoff, the air is relatively hot, making heat transfer difficult • Potential solution is to include battery power for takeoff and initial climb to reduce heat rejection requirement • Currently working on heat exchanger conceptual design to get initial size and weight Development of cryogenic materials and components evaluation 1. Multiscale model of laminate and ply microstructure – Cool to cryo and evaluate residual stresses per material system 2. NASTRAN/HyperX model of tank – Use HyperX with realistic thermo-mechanical load cases to evaluate optimized designs per material system 3. Progressive damage modeling to model microcracking and permeability – Laminate level or full multiscale FEM – Possibly beyond current resources Use multiscale progressive damage modeling to evaluate novel tank matrix material candidates (i.e. thermoplastics) under realistic thermo- mechanical loading with molecular dynamics data for the neat resin. Manufacturing demonstration of thermoplastic composite tank with new insulation materials. Tank Layup Micro Nano (MD) Commercial Aviation Propulsion Cycles and Utilization: The primary issues unique to aviation propulsion not directly addressed by current commercial transport technologies or NASA space propulsion revolve around the challenging transition of cryo-fuel handling and power/propulsion systems, from space propulsion applications having short lives, very low occupancy to commercial transport applications requiring much longer service lives, much higher occupancy and using high

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_021

**Systems:** lora_rag

**Claim:** Power-electronics components require thermal management in electrified aircraft because they are often operated outside their peak performance zone, and this can result in a thermal runaway scenario unless active thermal control features are available to mitigate this response.

**Cited evidence:**

- `C1` | `20205005005:chunk:00009`

of transport-class electrification can be nullified. Moreover, even an ideally 99%-efficient component will often be required to operate outside its peak performance zone, and this can result in a thermal runaway scenario unless active thermal control features are available to mitigate this response. It is therefore critically important to integrate an active thermal control system, such as TREES, with all the systems on the aircraft. Integrated Fault and Thermal Management Future electric aircraft propulsion systems will be based on the variety of configurations shown in Figure 16.6. Still, they all have in common the need to protect against electrical faults with DC breakers (indicated by the yellow dots) and to manage the waste heat produced by everything shown. Caption: Figure 16.6. Powertrain configurations require both thermal and fault management protection (yellow dots). (a) Parallel hybrid. (b) Turboelectric. (c) Series hybrid. (d) All electric. Credit: NASA Figure 16.7 depicts the TREES thermal management system (Dyson, 2019) integrated with a fault management system and applied to a Boeing 737 flight vehicle with parallel hybrid propulsion. The basic approach here is to extract high-exergy waste heat from the turbofan core using low–mass, SiC-coated graphite heat exchangers to thermoacoustically generate a ducted acoustic wave that is used to deliver mechanical energy throughout the aircraft. This acoustic energy can then operate a thermoacoustic heat pump to actively refrigerate the powertrain components while collecting the low- exergy waste heat from the powertrain and convert it to high-exergy useful heat, through which dynamically switchable heat pipes can then deliver throughout the aircraft for the beneficial applications shown in Table 16.3. Caption: Figure 16.7. TREES uses thermoacoustic and dynamically redirectable heat pipe tubes embedded in the aircraft to recycle both the turbofan and powertrain waste heat Credit: NASA Table 16.3. Beneficial Applications of Higher Exergy Waste Heat from

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_022

**Systems:** lora_rag

**Claim:** Fuel-cell thermal-management considerations include rejecting 40% to 60% of the fuel-cell heat energy, transitioning from LT PEM (80°C) to HT PEM (200°C) to achieve a large temperature differential between the coolant and airstream during takeoff and climb, placing the heat exchanger in the propulsor duct, and using battery power for takeoff and initial climb to reduce heat rejection requirements.

**Cited evidence:**

- `C1` | `20260003867:chunk:00010`

approaches for MW fuel cell stacks – Lightweight BOP , water and thermal management • Systems Analysis to assess new vehicle configurations Thermal Management System Considerations • Need to reject 40% to 60% of the fuel cell heat energy (~10 MWt) • Need to transition from LT PEM (80C) to HT PEM (200C) to achieve large temperature differential between coolant and airstream during takeoff and climb • Heat rejection must close at zero flight speed, necessitating the placement of the heat exchanger in the propulsor duct • At takeoff, the air is relatively hot, making heat transfer difficult • Potential solution is to include battery power for takeoff and initial climb to reduce heat rejection requirement • Currently working on heat exchanger conceptual design to get initial size and weight Development of cryogenic materials and components evaluation 1. Multiscale model of laminate and ply microstructure – Cool to cryo and evaluate residual stresses per material system 2. NASTRAN/HyperX model of tank – Use HyperX with realistic thermo-mechanical load cases to evaluate optimized designs per material system 3. Progressive damage modeling to model microcracking and permeability – Laminate level or full multiscale FEM – Possibly beyond current resources Use multiscale progressive damage modeling to evaluate novel tank matrix material candidates (i.e. thermoplastics) under realistic thermo- mechanical loading with molecular dynamics data for the neat resin. Manufacturing demonstration of thermoplastic composite tank with new insulation materials. Tank Layup Micro Nano (MD) Commercial Aviation Propulsion Cycles and Utilization: The primary issues unique to aviation propulsion not directly addressed by current commercial transport technologies or NASA space propulsion revolve around the challenging transition of cryo-fuel handling and power/propulsion systems, from space propulsion applications having short lives, very low occupancy to commercial transport applications requiring much longer service lives, much higher occupancy and using high

- `C2` | `20205005005:chunk:00007`

voltage, power, and current. It is also just as important to manage the significant new low-grade heat loads that are introduced each time an electrical component is added to the aircraft (Dooley, 2016); this was a primary consideration in the development of TREES. The challenges with low-grade waste heat in aircraft is five-fold because it  is not useful for work and difficult to reject  adds system mass from large heat exchangers, plumbing, and fluids  reduces net propulsive power from increased drag, compressor bleed, and turbine power extraction  has a limited thermal capacity due to sink temperature or surface availability  increases maintenance due to thermal management system complexity or structural integration challenges Caption: Figure 16.4 Heat sources distributed throughout the aircraft. (a) High-exergy (>20 MW). (b) Low-exergy (<1 MW). Credit: NASA As shown in Figure 16.4, aircraft have a range of heat sources distributed throughout the aircraft. High-exergy waste heat is emitted from the turbofan core, and low-exergy waste heat is distributed nearly everywhere else on the aircraft. The current approaches for managing this heat (Dooley, 2016), along with its drawbacks, are listed in Table 16.2. Table 16.2. Thermal Management Technology Options Thermal management technology Drawback Ram air heat exchanger Adds weight, aircraft drag, displaces fuel capacity Convective skin cooling heat exchanger Adds weight and drag, and requires liquid pumping losses Sinking heat into fuel Limited thermal capacity due to coking and volume Sinking heat into lubricating oil Limited thermal capacity; low T adds heat exchanger mass Active cooling Reduces propulsive efficiency; adds weight and maintenance Phase change cooling Limited thermal capacity; adds weight Heat pipe Does not increase exergy, which impacts mass and efficiency The heat pipe technology is shown as a drawback in Table 16.2 when used in isolation because it does not increase

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_023

**Systems:** lora_rag

**Claim:** Physics-based modeling and the development of an ultrasonic frequency domain technique sensitive to embedded battery defects are practical extensions of local ultrasonic resonance spectroscopy (LURS).

**Cited evidence:**

- `C1` | `20210025384:chunk:00039`

and simulated results. So far, this work has assumed a constant SOC for the battery, so further experimental efforts can be made on tracking battery resonances through charge/discharge cycles. Furthermore, the embedded defects used in this work were coarse to test the efficacy of the technique, so testing more subtle defect conditions can help determine the sensitivity of the technique. Such defect cases could be with smaller embedded chips or lab-grown dendrites and lithium plating. This work 45 focused on single-point measurements, so extending this technique into full battery scans could give insight into resonance changes across the entire battery. In addition, this work was done as a part of the NASA Convergent Aeronautics Solutions (CAS) project entitled Sensors based Prognostics to Avoid Runaway Reactions and Catastrophic Ignition (SPARRCI), which seeks to apply these types of inspection techniques to battery health monitoring with embedded sensors, machine learning, and prognostics tools. The multiphysics simulations have also laid the groundwork to support further inspection approaches of interest to the team, such as with bonded structural health monitoring (SHM) sensors or with guided wave approaches. This work will be continued through the end of 2022 by other NASA researchers working on the SPARRCI project. 46 References [1] B. Liu, J. G. Zhang, and W. Xu, “Advancing Lithium Metal Batteries,” Joule, vol. 2, no. 5, pp. 833–845, 2018, doi: 10.1016/j.joule.2018.03.008. [2] C. Hendricks, N. Williard, S. Mathew, and M. Pecht, “A failure modes, mechanisms, and effects analysis (FMMEA) of lithium-ion batteries,” J. Power Sources, vol. 297, pp. 113–120, 2015, doi: 10.1016/j.jpowsour.2015.07.100. [3] P. Sun, R. Bisschop, H. Niu, and X. Huang, A Review of Battery Fires in Electric Vehicles, no. May. 2020. [4] S. Sripad, A. Bills, and V. Viswanathan, “A review of safety considerations for batteries in aircraft with electric propulsion,” MRS Bull.,

- `C2` | `20210025384:chunk:00001`

team and for his constant advice and support throughout my time at LaRC. Also, Pat Johnston has been essential for providing feedback on my work with his vast expertise. Many thanks to Peter Juarez for training me on the lab equipment I needed to perform my work as well. In addition, I would like to thank the rest of the members of the NASA LaRC Nondestructive Evaluation Sciences Branch (NESB). While the mandatory teleworking made interacting with everybody a little unusual, I really enjoyed their joyous attitude and kindness every day. I would also like to extend my thanks to the rest of the SPARRCI team with whom I performed this work. Abstract As next-generation aircraft and vehicles continue to develop, so do their associated energy demands. Lithium metal batteries are a leading candidate to fulfill this energy requirement, but these batteries are prone to internal dendrite defects that can lead to catastrophic thermal runaway events. Current battery management systems are capable of mitigating such risks, but are unable to detect such defects until thermal runaway has already begun. Various nondestructive evaluation (NDE) techniques, particularly ultrasonic NDE, can directly monitor internal battery parameters giving them the potential to detect critical defects prior to catastrophic failure. However, most of the current battery NDE research has focused on improved battery state-of-charge (SOC) and state-of-health (SOH) monitoring with little emphasis on critical defect detection. Thus, a measurement technique sensitive to subtle battery defects is needed. In addition, the complex mechanics of ultrasound in porous, thin, multilayered batteries prompt the use of physics-based simulation to guide inspections. In this work, an ultrasonic NDE technique has been developed utilizing frequency domain analysis of local battery resonances to detect the presence of battery defects. This technique is a practical extension of local ultrasonic resonance spectroscopy (LURS)

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_024

**Systems:** base_rag

**Claim:** Thermoacoustic Heat Pump Systems

**Cited evidence:**

- `C2` | `20240015017:chunk:00001`

all components. The challenge s posed to stable TMS operation are dependent on several factors, such as high heat loads from electrical components and limited surface area of the aircraft for heat dissipation. Additionally, weight minimization of the thermal management system is needed to prevent further energetic losses. Current thermal management solutions have major disadvantages such as added weight, low thermal capacity, and no increase of exergy [3]. Table 1 contains the current approaches to managing dissipated thermal energy and their disadvantages. Inefficient TMS can lead to overheating of components, reduce system efficiency, and potential safety hazards. Therefore, developing innovative and effective thermal management architecture/infrastructure is crucial for the successful implementation of TMS systems within an electric aircraft. 1 Space and Aeronautics Research Engineer, Thermal Energy Conversion Branch, and AIAA Member. 2 Hybrid Gas Electric Propulsion Technical Lead, Thermal Energy Conversion Branch, and AIAA Member. 3Senior Research Engineer, Optics and Photonics Branch, AIAA Associate Fellow 4Research Engineer, Thermal Energy Conversion Branch, AIAA Membe r 2025 AIAA SciTech Forum, Orlando, Florida January 6-10, 2025 2 TREES was developed as a novel approach that may solve the disadvantages of the current TMS technologies [3]. A full-scale sized aircraft TREES system can harness the high-grade waste heat, that is wasted by fully electric or hybrid electric aircraft, and convert it to acoustic energy via entry stages called thermal amplifiers [4]. Sources of high and low-grade heat are shown in Figure 1. This system will operate by first converting the incoming thermal energy into acoustic energy. Subsequently, the acoustic energy is channeled through a network of tubes leading to acoustic heat pumps. Within the heat pumps, the acoustic energy converts back to low-grade thermal energy. Finally, the low- grade heat from the acoustic pump can be distributed and reused throughout the aircraft via a

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_025

**Systems:** base_rag

**Claim:** This only passively prevents thermal runaway from occurring and adds significant weight to the batteries, which is very undesirable in aerospace applications.

**Cited evidence:**

- `C2` | `20170007959:chunk:00014`

amount of power lost to heat is closely dependent on battery discharge rate and state of charge. Improving this model is the subject of additional work. 8 With a well-characterized cell, a sample X-57 Mod II mission proﬁle was applied in Figure 10. From an initial temperature of 35 C (a “hot day” ground condition for Armstrong Flight Research Center), the isolated cell experiences a total adiabatic temperature rise of 30 C. The most stressful phases are the full-power ground roll (takeo ↵) and climb segments. Battery thermal runaway is a risk above 60 C, and propagation between cells can result in a cascading failure of an entire battery module. At least for the “hot day” conditions, it is useful to deﬁne a required minimum cooler to stabilize the battery temperature. As a thermal sizing model, it is ﬂexible enough to accept a generic cooling load of the form, Tn+1 = Tn + Pcruise ⌘ (Tn T0)h Nconf igcpm (10) where the expression ( Tn T0) ⇤ h describes a generic cooler, with a rate proportional to the temperature 9o f 13 American Institute of Aeronautics and Astronautics di↵erence between the cell and the environment. An overall heat transfer coe cient, h, can be chosen such that the simulated cell temperature never exceeds a predetermined safe operating limit. For the Mod II ﬂight proﬁle, h = 25 W m2 K is su cient: Figure 10. T emperature transients with various hypothetical cooling rates The simplicity and ﬂexibility of the lumped capacitance thermal script makes it a powerful tool for testing combinations of cooling schemes and ﬂight proﬁles. Future work will incorporate dynamic polarization models, to better capture transients and state e ↵ects of the battery. This will better quantify non-linear thermal and voltage e↵ects due to state of charge, temperature,

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_026

**Systems:** lora_rag

**Claim:** Nondestructive evaluation techniques can detect geometry and material properties associated with each of these defect mechanisms and are sensitive to wave propagation and wave-defect interaction within the battery.

**Cited evidence:**

- `C2` | `20210025384:chunk:00007`

changes in geometry and material properties associated with each of these defect mechanisms and thus the potential for detection based on the amount of influence they have on wave propagation and wave-defect interaction within the battery. Current Battery Monitoring Techniques 1.2.1 Battery Management Systems As mentioned before, the current solution to prevent dendrites from causing thermal runaway is to engineer safe containment systems and constantly monitor the batteries. These tasks are accomplished with a battery management system (BMS) which is used to ensure maximum operating efficiency and mitigate battery failure. The most basic way in which a BMS does this is through the state of charge (SOC) and state of health (SOH) monitoring. The SOC of a battery is the ratio of the battery’s current charge to its maximum capacity and is the most important of these parameters as it is essentially the ‘fuel gauge’ that can determine how much energy is left in the battery. The battery’s SOH is representative of the battery’s deterioration from aging and is usually tracked by monitoring changes in maximum SOC over time. There are various different SOC and SOH estimation algorithms and models, but they mostly all involve using external cell parameters such as voltage, current, and temperature as inputs for lookup tables and computational models that then predict the overall SOC [9]. As these methods all lack information about internal battery changes, there is a degree of inaccuracy to their predictions that can accumulate in error over time. For this same reason, these methods are not 5 sensitive to the development of some critical battery defects [2]. Ultrasonic nondestructive evaluation (NDE) techniques, however, have the advantage of directly monitoring internal battery changes, thus making them effective at SOC/SOH monitoring and also sensitive to defects, and is why they have been of great

- `C4` | `20210025384:chunk:00006`

as the solid electrolyte interface (SEI). In this layer, lithium plating can occur in which lithium ions are reduced to metallic lithium and build up at the interface. This lithium is no longer usable in standard battery operation and will thus result in an overall loss of charge capacity. This is a normal aging phenomenon in lithium-based batteries and is generally why these types of batteries have a limited lifetime. However, under various cycling conditions, such as low temperature or high charge/discharge rates, this plating can occur non-uniformly and form needle-like structures known as dendrites. Dendrites can penetrate the battery separator, short circuit the electrodes, and cause a thermal runaway reaction to occur [8]. This process is further emphasized in Figure 2. Figure 2: Conceptual sketch of how lithium plating can lead to dendrite growth Dendrites have received lots of attention due to their common occurrence, their potential for catastrophic failure, and their difficulty of detection. However, there are other important battery defects that can occur [2]. Gas generation from the decomposition of the electrolyte solvent can Lithium Anode Separator/Electrolyte Li+ Li+ Separator/Electrolyte Lithium Anode Li SEI SEI Dendrites Lithium Anode Separator/Electrolyte Li+ Li+ Li+ SEI e- 4 lead to increased cell temperatures and thus thermal runaway. Continued reduction of lithium ions can cause further thickening of the SEI layer and an overall loss in charge capacity and performance of the battery. From an ultrasonic NDE perspective, there are local changes in geometry and material properties associated with each of these defect mechanisms and thus the potential for detection based on the amount of influence they have on wave propagation and wave-defect interaction within the battery. Current Battery Monitoring Techniques 1.2.1 Battery Management Systems As mentioned before, the current solution to prevent dendrites from causing thermal runaway is to engineer

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_027

**Systems:** base_rag

**Claim:** E1

**Cited evidence:**

- `C1` | `20205005005:chunk:00009`

of transport-class electrification can be nullified. Moreover, even an ideally 99%-efficient component will often be required to operate outside its peak performance zone, and this can result in a thermal runaway scenario unless active thermal control features are available to mitigate this response. It is therefore critically important to integrate an active thermal control system, such as TREES, with all the systems on the aircraft. Integrated Fault and Thermal Management Future electric aircraft propulsion systems will be based on the variety of configurations shown in Figure 16.6. Still, they all have in common the need to protect against electrical faults with DC breakers (indicated by the yellow dots) and to manage the waste heat produced by everything shown. Caption: Figure 16.6. Powertrain configurations require both thermal and fault management protection (yellow dots). (a) Parallel hybrid. (b) Turboelectric. (c) Series hybrid. (d) All electric. Credit: NASA Figure 16.7 depicts the TREES thermal management system (Dyson, 2019) integrated with a fault management system and applied to a Boeing 737 flight vehicle with parallel hybrid propulsion. The basic approach here is to extract high-exergy waste heat from the turbofan core using low–mass, SiC-coated graphite heat exchangers to thermoacoustically generate a ducted acoustic wave that is used to deliver mechanical energy throughout the aircraft. This acoustic energy can then operate a thermoacoustic heat pump to actively refrigerate the powertrain components while collecting the low- exergy waste heat from the powertrain and convert it to high-exergy useful heat, through which dynamically switchable heat pipes can then deliver throughout the aircraft for the beneficial applications shown in Table 16.3. Caption: Figure 16.7. TREES uses thermoacoustic and dynamically redirectable heat pipe tubes embedded in the aircraft to recycle both the turbofan and powertrain waste heat Credit: NASA Table 16.3. Beneficial Applications of Higher Exergy Waste Heat from

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_028

**Systems:** lora_rag

**Claim:** Active cooling can reduce the battery pack's weight by using an efficient cooling system, but it requires an additional cooling pump and power.

**Cited evidence:**

- `C1` | `20240014672:chunk:00001`

cooling pump power and battery weight, respectively, and the maximal temperature constraint is satisfied. This work has the potential to reduce battery-pack weight, improve performance, and reduce the weight of thermal management systems for electric vertical take-off and landing aircraft. I. Introduction Thermal management is essential for battery packs in electric aircraft, which lack the natural heat dissipation of conventional air-breathing engines [1]. Accumulated heat can damage batteries and other components, compromising the safety and performance of the aircraft. There are two primary methods for cooling the battery: passive and active. Passive cooling has the advantage of not requiring additional pumps or power, but it typically requires a greater surface area dedicated to heat rejection to the external environment, thereby increasing the overall weight of the battery pack. In contrast, active cooling can significantly reduce the battery pack weight, but it requires an efficient cooling system design to offset the added weight and power of the cooling pump [2]. Because ambient air is a readily available resource for aircraft, this paper considers an active cooling concept with forced convection of ambient air through the battery pack. Conjugate heat transfer (CHT) optimization is a powerful approach to designing high-performance active cooling battery packs. It enables more realistic aero-thermal coupling by integrating computational fluid dynamics (CFD) to simulate fluid domains and conduction heat transfer solvers for the solid domains. The CHT optimization method has been used to analyze the aerodynamics and heat transfer of various battery pack shapes and flow conditions [3, 4]. CHT-based design optimization studies have also been conducted to improve ∗Assistant Professor, Department of Aerospace Engineering, AIAA Senior Member. Email: phe@iastate.edu †PhD Student, Department of Aerospace Engineering, AIAA Student Member. ‡PhD Student, Department of Aerospace Engineering, AIAA Student Member. §Research Engineer, Propulsion Systems Analysis Branch, AIAA Member. 1 performance[5];however,inthisstudy,agradient-freeoptimizationalgorithmwasused.

- `C2` | `20240014672:chunk:00000`

Aerothermal Shape Optimization of Actively-Cooled Battery Packs using Conjugate Heat Transfer Ping He∗, Christian A. Psenica†, and Lean Fang‡ Iowa State University, Ames, IA 50011 Mark K. Leader§ NASA Glenn Research Center, Cleveland, OH 44135 Thermal management for batteries is important for electric aircraft because battery temperature is critically important to vehicle safety, and it also has a direct impact on the efficiency of the battery system. Because ambient air is a readily available resource for aircraft, this paper considers an active cooling concept with forced convection of ambient air through the battery pack. Conjugate heat transfer analysis is used to solve the coupled aero-thermal problem, which consists of a finite-volume computational fluid dynamics solver for the fluid domain, and a conduction heat transfer solver for the solid domain. A mixed Neumann and Dirichlet boundary condition is developed for the fluid-solid interface, which allows the solid domain to completely submerge in the fluid domain. A gradient-based optimization method is adopted, and the discrete adjoint approach implemented in DAFoam is used to efficiently compute the gradients. The aero-thermal coupling for primal analysis and gradient computation is handled using the OpenMDAO-based MPhys framework. A constant heat source is prescribed for the battery cells, and the battery shape (design variable) is optimized to minimize cooling pump power and battery weight (composite objective function) while keeping the battery temperature below a threshold (constraint). The optimized design achieves a 44.6% and 1.5% reduction in the cooling pump power and battery weight, respectively, and the maximal temperature constraint is satisfied. This work has the potential to reduce battery-pack weight, improve performance, and reduce the weight of thermal management systems for electric vertical take-off and landing aircraft. I. Introduction Thermal management is essential for battery packs in electric aircraft, which lack the natural heat dissipation of conventional

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_029

**Systems:** lora_rag

**Claim:** Ultrasonic NDE can directly monitor internal battery parameters and detect critical defects prior to catastrophic failure.

**Cited evidence:**

- `C1` | `20210025384:chunk:00039`

and simulated results. So far, this work has assumed a constant SOC for the battery, so further experimental efforts can be made on tracking battery resonances through charge/discharge cycles. Furthermore, the embedded defects used in this work were coarse to test the efficacy of the technique, so testing more subtle defect conditions can help determine the sensitivity of the technique. Such defect cases could be with smaller embedded chips or lab-grown dendrites and lithium plating. This work 45 focused on single-point measurements, so extending this technique into full battery scans could give insight into resonance changes across the entire battery. In addition, this work was done as a part of the NASA Convergent Aeronautics Solutions (CAS) project entitled Sensors based Prognostics to Avoid Runaway Reactions and Catastrophic Ignition (SPARRCI), which seeks to apply these types of inspection techniques to battery health monitoring with embedded sensors, machine learning, and prognostics tools. The multiphysics simulations have also laid the groundwork to support further inspection approaches of interest to the team, such as with bonded structural health monitoring (SHM) sensors or with guided wave approaches. This work will be continued through the end of 2022 by other NASA researchers working on the SPARRCI project. 46 References [1] B. Liu, J. G. Zhang, and W. Xu, “Advancing Lithium Metal Batteries,” Joule, vol. 2, no. 5, pp. 833–845, 2018, doi: 10.1016/j.joule.2018.03.008. [2] C. Hendricks, N. Williard, S. Mathew, and M. Pecht, “A failure modes, mechanisms, and effects analysis (FMMEA) of lithium-ion batteries,” J. Power Sources, vol. 297, pp. 113–120, 2015, doi: 10.1016/j.jpowsour.2015.07.100. [3] P. Sun, R. Bisschop, H. Niu, and X. Huang, A Review of Battery Fires in Electric Vehicles, no. May. 2020. [4] S. Sripad, A. Bills, and V. Viswanathan, “A review of safety considerations for batteries in aircraft with electric propulsion,” MRS Bull.,

- `C2` | `20210025384:chunk:00001`

team and for his constant advice and support throughout my time at LaRC. Also, Pat Johnston has been essential for providing feedback on my work with his vast expertise. Many thanks to Peter Juarez for training me on the lab equipment I needed to perform my work as well. In addition, I would like to thank the rest of the members of the NASA LaRC Nondestructive Evaluation Sciences Branch (NESB). While the mandatory teleworking made interacting with everybody a little unusual, I really enjoyed their joyous attitude and kindness every day. I would also like to extend my thanks to the rest of the SPARRCI team with whom I performed this work. Abstract As next-generation aircraft and vehicles continue to develop, so do their associated energy demands. Lithium metal batteries are a leading candidate to fulfill this energy requirement, but these batteries are prone to internal dendrite defects that can lead to catastrophic thermal runaway events. Current battery management systems are capable of mitigating such risks, but are unable to detect such defects until thermal runaway has already begun. Various nondestructive evaluation (NDE) techniques, particularly ultrasonic NDE, can directly monitor internal battery parameters giving them the potential to detect critical defects prior to catastrophic failure. However, most of the current battery NDE research has focused on improved battery state-of-charge (SOC) and state-of-health (SOH) monitoring with little emphasis on critical defect detection. Thus, a measurement technique sensitive to subtle battery defects is needed. In addition, the complex mechanics of ultrasound in porous, thin, multilayered batteries prompt the use of physics-based simulation to guide inspections. In this work, an ultrasonic NDE technique has been developed utilizing frequency domain analysis of local battery resonances to detect the presence of battery defects. This technique is a practical extension of local ultrasonic resonance spectroscopy (LURS)

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

---

## claimrev_030

**Systems:** lora_rag

**Claim:** Safety-related standards and regulations may implicitly assume both a liquid fossil fuel energy source and an attendant fire hazard, but they do not address the hazards introduced by the use of a battery pack of the construction and capacity required by a hybrid-electric propulsion system.

**Cited evidence:**

- `C1` | `20190033416:chunk:00018`

But many FUELEAP stakeholders —systems engineers, electrical and avionics engineers, pilots, safety specialists, and regulators—will be unfamiliar with both the safety and operational concerns surrounding hybrid electric propulsion and the relative merits of means of addressing these. Such stakeholders might benefit from a guide to how power system des ign fit into in the ‘big picture’ of aircraft safety. One way the safety argument augments our modeling and safety assessment activities is by explaining that story to readers. Fig. 4 The top-level of the FUELEAP safety argument in the Goal Structuring Notation (Ref 15) When means of addressing aircraft hazards or assessing aircraft safety are familiar, it may not be necessary to explain these to readers beyond, perhaps, referencing applicable standards. Safety-related standards and regulations often serve to define best practice, capturing judgments about which hazards require mitigation and sometimes what mitigations are advisable and how they should be assessed. But these judgments might not be universally applicable. For example, 14CFR §23.2430.a.2 requires that aircraft fuel systems be “designed and arranged to prevent ignition of the fuel within the system by direct lightning strikes … or by corona or streamering at fuel vent outlets,” thus implicitly presuming both a liquid fossil fuel energy source and an attendant fire hazard. But it makes no mention of the hazards introduced by the use of a battery pack of the construction and capacity required by a hybrid power 9 system. By capturing the hazards that FUELEAP’s project team envision and relating these hazards to mitigations, the safety argument records the team’s contention as to which unique hazards require mitigation and what means of mitigation should be considered sufficient. The argument will thus serve as the starting poi nt for discussing these matters with relevant regulators, including the NASA ASRB. FUELEAP’s nature as a

**Decision:** `SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED / CONTRADICTED`

**Note:**

